import re
import json
import ast

from pymongo.errors import ConnectionFailure

from django.db import ProgrammingError
from django.db import connection

from models import Query

from explorer import app_settings
from rdrf.utils import mongo_db_name_reg_id
from rdrf.mongo_client import construct_mongo_client
from rdrf.models import Registry, RegistryForm, Section, CommonDataElement
from models import Query
from forms import QueryForm

import logging
logger = logging.getLogger("registry_log")


class MissingDataError(Exception):
    pass


class DatabaseUtils(object):

    result = None

    def __init__(self, form_object=None, verify=False):
        if form_object and isinstance(form_object, QueryForm):
            self.form_object = form_object
            self.query = form_object['sql_query'].value()
            self.registry_id = self.form_object['registry'].value()
            if not verify:
                self.collection = self.form_object['collection'].value()
                self.criteria = self._string_to_json(self.form_object['criteria'].value())
                self.projection = self._string_to_json(self.form_object['projection'].value())
                self.aggregation = self.form_object['aggregation'].value()
                self.mongo_search_type = self.form_object['mongo_search_type'].value()
        elif form_object and isinstance(form_object, Query):
            self.form_object = form_object
            self.query = form_object.sql_query
            self.registry_id = self.form_object.registry.id
            if not verify:
                self.collection = self.form_object.collection
                self.criteria = self._string_to_json(self.form_object.criteria)
                self.projection = self._string_to_json(self.form_object.projection)
                self.aggregation = self.form_object.aggregation
                self.mongo_search_type = self.form_object.mongo_search_type

    def connection_status(self):
        try:
            client = self._get_mongo_client()
            client.close()
            return True, None
        except ConnectionFailure as e:
            return False, e

    def run_sql(self):
        try:
            cursor = self.create_cursor()
            self.result = self._dictfetchall(cursor)
        except ProgrammingError as error:
            self.result = {'error_msg': error.message}

        return self

    def dump_results_into_reportingdb(self, reporting_table_generator):
        logger.debug("*********** running query and dumping to temporary table *******")
        reporting_table_generator.drop_table()
        logger.debug("dropped temporary table")
        self.cursor = self.create_cursor()
        sql_metadata = self._get_sql_metadata(self.cursor)
        logger.debug("sql metadata = %s" % sql_metadata)
        mongo_metadata = self._get_mongo_metadata()
        logger.debug("mongo metadata = %s" % mongo_metadata)

        reporting_table_generator.create_columns(sql_metadata, mongo_metadata)
        reporting_table_generator.create_schema()
        reporting_table_generator.run_explorer_query(self)

    def generate_results(self, reverse_column_map):
        logger.debug("generate_results ...")
        self.reverse_map = reverse_column_map
        self.mongo_client = self._get_mongo_client()
        logger.debug("created mongo client")
        self.database = self.mongo_client[mongo_db_name_reg_id(self.registry_id)]
        collection = self.database[self.collection]
        logger.debug("retrieving mongo models for projection once off")
        self.mongo_models = [model_triple for model_triple in self._get_mongo_fields()]
        logger.debug("iterating through sql cursor ...")

        for row in self.cursor:
            logger.debug("sql row = %s" % str(row))
            sql_columns_dict = {}
            for i, item in enumerate(row):
                logger.debug("item %s = %s" % (i, item))
                sql_column_name = self.reverse_map[i]
                logger.debug("sql_column_name = %s" % sql_column_name)
                sql_columns_dict[sql_column_name] = item

            for mongo_columns_dict in self.run_mongo_one_row(sql_columns_dict, collection):
                for combined_dict in self._combine_sql_and_mongo(sql_columns_dict, mongo_columns_dict):
                    yield combined_dict

    def _combine_sql_and_mongo(self, sql_result_dict, mongo_result_dict):
        logger.debug("combining results of mongo and sql")

        logger.debug("sql_result_dict = %s" % str(sql_result_dict))
        logger.debug("mongo result = %s" % str(mongo_result_dict))

        combined_dict = {}
        combined_dict.update(sql_result_dict)
        combined_dict.update(mongo_result_dict)

        # potentially unwind all multisection cdes here ...
        if False:
            # TO DO!
            # row contains multisection values for one or more fields
            for unwound_dict in self._unwind(combined_dict):
                yield unwound_dict
        else:
            # row contains no multisection cdes
            yield combined_dict

    def _unwind(self, combined_dict):
        # vector product of multisection cdes
        # to do
        yield "todo"

    def _get_sql_type_info(self):
        #reporting=# select oid, typname,typcategory from pg_type;;
        # oid  |                typname                | typcategory
        # -------+---------------------------------------+-------------
        # 16 | bool                                  | B
        # 17 | bytea                                 | U
        # 18 | char                                  | S
        # 19 | name                                  | S
        # 20 | int8                                  | N
        # 21 | int2                                  | N
        # ...
        # 705 | unknown                               | X
        # 718 | circle                                | G
        # 719 | _circle                               | A
        # 790 | money                                 | N
        # 791 | _money                                | A
        # 829 | macaddr                               | U
        # 869 | inet                                  | I
        # 650 | cidr                                  | I
        # ...
        # ...
        cursor = connection.cursor()
        # see http://www.postgresql.org/docs/current/static/catalog-pg-type.html
        type_info_sql = "select oid, typname from pg_type"
        cursor.execute(type_info_sql)
        type_dict = {}
        for row in cursor:
            oid = row[0]
            type_name = row[1]
            type_dict[oid] = type_name
        return type_dict

    def _get_sql_metadata(self, cursor):
        import sqlalchemy as alc
        # type_code is looked up in the oid map
        # cursor description gives list:
        #[Column(name='id', type_code=23, display_size=None, internal_size=4, precision=None, scale=None, null_ok=None),
        # Column(name='family_name', type_code=1043, display_size=None, internal_size=100, precision=None, scale=None, null_ok=None),
        # Column(name='given_names', type_code=1043, display_size=None, internal_size=100, precision=None, scale=None, null_ok=None), Column(name='date_of_birth', type_code=1082, display_size=None, internal_size=4, precision=None, scale=None, null_ok=None), Column(name='Working Group', type_code=1043, display_size=None, internal_size=100, precision=None, scale=None, null_ok=None)]

        if cursor is None:
            return []

        type_info = self._get_sql_type_info()

        def get_info(item):
            name = item.name
            type_code = item.type_code
            type_name = type_info.get(type_code, "varchar")

            return {"name": name, "type_name": type_name}

        return [get_info(item) for item in cursor.description]

    def create_cursor(self):
        logger.debug("creating cursor from sql query: %s" % self.query)
        cursor = connection.cursor()
        cursor.execute(self.query)
        return cursor

    def _get_mongo_metadata(self):
        import json
        from rdrf.models import Registry, RegistryForm, Section, CommonDataElement
        from rdrf.utils import forms_and_sections_containing_cde

        def short_column_name(form_model, section_model, cde_code):
            return form_model.name[:5] + "_" + section_model.code + "_" + cde_model.code

        registry_model = Registry.objects.get(pk=self.registry_id)
        data = {"column_map": {}}

        for cde_dict in self.projection:
            form_model = RegistryForm.objects.get(name=cde_dict["formName"])
            section_model = Section.objects.get(code=cde_dict["sectionCode"])
            cde_model = CommonDataElement.objects.get(code=cde_dict["cdeCode"])
            forms_sections = forms_and_sections_containing_cde(registry_model, cde_model)
            if len(forms_sections) == 1:
                using_form = forms_sections[0][0]
                using_section = forms_sections[0][1]
                if using_form.name == form_model.name and using_section.code == section_model.code:
                    # we can safely just use the cde code as the column name
                    data["column_map"][(form_model, section_model, cde_model)] = cde_model.code
                else:
                    # error?
                    raise Exception("mongo projection cde not in registry")
            else:
                # another form or section on the same form is using this cde too
                # use an abbreviation
                data["column_map"][(form_model, section_model, cde_model)] = short_column_name(form_model,
                                                                                               section_model,
                                                                                               cde_model)
        return data

    def _get_mongo_fields(self):
        # to do!
        for cde_dict in self.projection:
            logger.debug("cde_dict = %s" % cde_dict)
            form_model = RegistryForm.objects.get(name=cde_dict["formName"])
            section_model = Section.objects.get(code=cde_dict["sectionCode"])
            cde_model = CommonDataElement.objects.get(code=cde_dict["cdeCode"])

            yield form_model, section_model, cde_model

    def run_mongo_one_row(self, sql_column_data, mongo_collection):
        logger.debug("getting mongo data for one patient")
        django_model = "Patient"
        django_id = sql_column_data["id"]  # convention?
        logger.debug("django_id =%s" % django_id)
        mongo_query = {"django_model": django_model,
                       "django_id": django_id}

        logger.debug("mongo_query = %s" % mongo_query)

        for mongo_document in mongo_collection.find(mongo_query):
            result = {}
            result["context_id"] = mongo_document.get("context_id", None)
            logger.debug("context_id = %s" % result["context_id"])
            for form_model, section_model, cde_model in self.mongo_models:
                column_name = self.reverse_map[(form_model, section_model, cde_model)]
                column_value = self._get_cde_value(form_model,
                                                         section_model,
                                                         cde_model,
                                                         mongo_document)
                result[column_name] = column_value
                logger.debug("django id %s mongo column %s = %s" % (django_id, column_name, column_value))
            yield result

    def _get_cde_value(self, form_model, section_model, cde_model, mongo_document):
        # retrieve value of cde
        for form_dict in mongo_document["forms"]:
            if form_dict["name"] == form_model.name:
                for section_dict in form_dict["sections"]:
                    if section_dict["code"] == section_model.code:
                        if section_dict["allow_multiple"]:
                            values = []
                            for section_item in section_dict["cdes"]:
                                for cde_dict in section_item:
                                    if cde_dict["code"] == cde_model.code:
                                        values.append(self._get_sensible_value_from_cde(cde_model, cde_dict["value"]))
                            return values
                        else:
                            logger.debug("section_dict = %s" % section_dict)
                            for cde_dict in section_dict["cdes"]:
                                if cde_dict["code"] == cde_model.code:
                                    return self._get_sensible_value_from_cde(cde_model, cde_dict["value"])

    def _get_sensible_value_from_cde(self, cde_model, stored_value):
        if cde_model.datatype == "file":
            return "FILE"  # to do
        else:
            return stored_value

    def run_mongo(self):
        client = self._get_mongo_client()
        projection = {}
        criteria = {}
        database = client[mongo_db_name_reg_id(self.registry_id)]
        collection = database[self.collection]

        mongo_search_type = self.mongo_search_type

        criteria = self.criteria
        projection = self.projection

        django_ids = []
        if self.result:
            for r in self.result:
                django_ids.append(r["id"])

        records = []
        if mongo_search_type == 'F':
            criteria["django_id"] = {"$in": django_ids}
            results = collection.find(criteria, projection)
        elif mongo_search_type == 'A':
            aggregation = []
    
            pipline = self.aggregation.split("|")
            for pipe in pipline:
                aggregation.append(ast.literal_eval(pipe))
        
            if "$match" in aggregation:
                aggregation["$match"].update({"django_id": {"$in": django_ids}})
            else:
                aggregation.append({"$match": {"django_id": {"$in": django_ids}}})
            results = collection.aggregate(aggregation)
            results = results['result']

        for cur in results:
            row = {}
            for k in cur:
                if isinstance(cur[k], (dict)):
                    for key, value in cur[k].iteritems():
                        row[key] = value
                else:
                    row[k] = cur[k]
            records.append(row)

        self.result = records
        return self

    def run_full_query(self):
        sql_result = self.run_sql().result
        mongo_result = self.run_mongo().result

        self.result = []
        for sr in sql_result:
            for mr in mongo_result:
                if sr['id'] == int(mr['django_id']):
                    mr.update(sr)
                    self.result.append(mr)

        return self


    def run_full_query_split(self):
        sql_result = self.run_sql().result
        mongo_result = self.run_mongo().result
        return sql_result, mongo_result

    def _string_to_json(self, string):
        try:
            return json.loads(string)
        except ValueError:
            return None

    def _dictfetchall(self, cursor):
        "Returns all rows from a cursor as a dict"
        desc = cursor.description
        return [
            dict(zip([col[0] for col in desc], row))
            for row in cursor.fetchall()
        ]

    def _get_mongo_client(self):
        return construct_mongo_client()


class ParseQuery(object):

    def get_parameters(query):
        pass

    def set_parameters(query):
        pass
