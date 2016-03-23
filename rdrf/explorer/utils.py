import re
import json
import ast

from pymongo.errors import ConnectionFailure

from django.db import ProgrammingError
from django.db import connection

from models import Query

from explorer import app_settings
from rdrf.utils import mongo_db_name_reg_id
from rdrf.utils import forms_and_sections_containing_cde, get_cached_instance
from rdrf.utils import timed
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
            self.registry_model = Registry.objects.get(pk=self.registry_id)
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
            self.registry_model = Registry.objects.get(pk=self.registry_id)
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

    @timed
    def dump_results_into_reportingdb(self, reporting_table_generator):
        logger.debug("*********** running query and dumping to temporary table *******")
        try:
            reporting_table_generator.drop_table()
        except Exception, ex:
            logger.error("Report Error: dropping table: %s" % ex)
            raise

        logger.debug("dropped temporary table")

        try:
            self.cursor = self.create_cursor()
        except Exception, ex:
            logger.error("Report Error: create cursor: %s" % ex)
            raise

        try:
            sql_metadata = self._get_sql_metadata(self.cursor)
        except Exception, ex:
            logger.error("Report Error: getting sql metadata: %s" % ex)
            raise

        try:
            mongo_metadata = self._get_mongo_metadata()
        except Exception, ex:
            logger.error("Report Error: getting mongo metadata: %s" % ex)
            raise

        try:
            reporting_table_generator.create_columns(sql_metadata, mongo_metadata)
        except Exception, ex:
            logger.error("Report Error: creating columns: %s" % ex)
            raise

        try:
            reporting_table_generator.create_schema()
        except Exception, ex:
            logger.error("Report Error: creating schema: %s" % ex)
            raise

        try:
            reporting_table_generator.run_explorer_query(self)
        except Exception, ex:
            logger.error("Error running explorer query: %s" % ex)
            raise

    @timed
    def generate_results(self, reverse_column_map):
        logger.debug("generate_results ...")
        self.reverse_map = reverse_column_map
        self.mongo_client = self._get_mongo_client()
        logger.debug("created mongo client")
        self.database = self.mongo_client[mongo_db_name_reg_id(self.registry_id)]
        collection = self.database[self.collection]
        history_collection = self.database["history"]

        logger.debug("retrieving mongo models for projection once off")
        if self.projection:
            self.mongo_models = [model_triple for model_triple in self._get_mongo_fields()]
        else:
            self.mongo_models = []

        logger.debug("iterating through sql cursor ...")

        if self.mongo_search_type == "C":
            logger.debug("CURRENT MONGO REPORT")
            # current data - no longitudinal snapshots
            for row in self.cursor:
                sql_columns_dict = {}
                for i, item in enumerate(row):
                    sql_column_name = self.reverse_map[i]
                    sql_columns_dict[sql_column_name] = item

                for mongo_columns_dict in self.run_mongo_one_row(sql_columns_dict, collection):
                    mongo_columns_dict["snapshot"] = False
                    for combined_dict in self._combine_sql_and_mongo(sql_columns_dict, mongo_columns_dict):
                        yield combined_dict
        else:
            # include longitudinal ( snapshot) data
            logger.debug("LONGITUDINAL MONGO REPORT")
            for row in self.cursor:
                sql_columns_dict = {}
                for i, item in enumerate(row):
                    sql_column_name = self.reverse_map[i]
                    sql_columns_dict[sql_column_name] = item

                for mongo_columns_dict in self.run_mongo_one_row(sql_columns_dict, collection):
                    mongo_columns_dict["snapshot"] = False
                    for combined_dict in self._combine_sql_and_mongo(sql_columns_dict, mongo_columns_dict):
                        yield combined_dict

                for mongo_columns_dict in self.run_mongo_one_row_longitudinal(sql_columns_dict, history_collection):
                    mongo_columns_dict["snapshot"] = True
                    for combined_dict in self._combine_sql_and_mongo(sql_columns_dict, mongo_columns_dict):
                        yield combined_dict

    def _combine_sql_and_mongo(self, sql_result_dict, mongo_result_dict):
        combined_dict = {}
        combined_dict.update(sql_result_dict)
        combined_dict.update(mongo_result_dict)
        yield combined_dict

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

    @timed
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

    @timed
    def create_cursor(self):
        logger.debug("creating cursor from sql query: %s" % self.query)
        cursor = connection.cursor()
        cursor.execute(self.query)
        return cursor

    @timed
    def _get_mongo_metadata(self):
        data = {"multisection_column_map": {}}

        if not self.projection:
            return data

        logger.debug("number of projections = %s" % len(self.projection))

        for cde_dict in self.projection:
            form_model = RegistryForm.objects.get(name=cde_dict["formName"], registry=self.registry_model)
            section_model = Section.objects.get(code=cde_dict["sectionCode"])
            cde_model = CommonDataElement.objects.get(code=cde_dict["cdeCode"])
            column_name = self._get_database_column_name(form_model, section_model, cde_model)
            data["multisection_column_map"][(form_model, section_model, cde_model)] = column_name
        return data

    def _get_database_column_name(self, form_model, section_model, cde_model):
        return "column_%s_%s_%s" % (form_model.pk,
                                    section_model.pk,
                                    cde_model.pk)

    def _get_mongo_fields(self):
        logger.debug("getting mongo fields from projection")
        for cde_dict in self.projection:
            form_model = get_cached_instance(RegistryForm, name=cde_dict["formName"], registry=self.registry_model)
            section_model = get_cached_instance(Section, code=cde_dict["sectionCode"])
            cde_model = get_cached_instance(CommonDataElement, code=cde_dict["cdeCode"])

            yield form_model, section_model, cde_model


    def run_mongo_one_row(self, sql_column_data, mongo_collection):
        django_model = "Patient"
        django_id = sql_column_data["id"]  # convention?
        mongo_query = {"django_model": django_model,
                       "django_id": django_id}

        for mongo_document in mongo_collection.find(mongo_query):
            result = {}
            result["context_id"] = mongo_document.get("context_id", None)
            result['timestamp'] = mongo_document.get("timestamp", None)
            for form_model, section_model, cde_model in self.mongo_models:
                column_name = self.reverse_map[(form_model, section_model, cde_model)]
                column_value = self._get_cde_value(form_model,
                                                         section_model,
                                                         cde_model,
                                                         mongo_document)

                result[column_name] = column_value
            yield result

    def run_mongo_one_row_longitudinal(self, sql_column_data, history_collection):
        django_id = sql_column_data["id"]

        mongo_query = {"django_id": django_id,
                       "django_model": "Patient",
                       "record_type": "snapshot"}


        for snapshot_document in history_collection.find(mongo_query):
            result = {}
            result["timestamp"] = snapshot_document["timestamp"]
            result["context_id"] = snapshot_document["record"].get("context_id", None)
            for form_model, section_model, cde_model in self.mongo_models:
                column_name = self.reverse_map[(form_model, section_model, cde_model)]
                column_value = self._get_cde_value(form_model,
                                                   section_model,
                                                   cde_model,
                                                   snapshot_document["record"])
                result[column_name] = column_value


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
                            for cde_dict in section_dict["cdes"]:
                                if cde_dict["code"] == cde_model.code:
                                    value = self._get_sensible_value_from_cde(cde_model, cde_dict["value"])
                                    return value

        if section_model.allow_multiple:
            # no data filled in?
            return [None]
        else:
            return None

    def _get_sensible_value_from_cde(self, cde_model, stored_value):
        if cde_model.datatype == "file":
            return "FILE"  # to do
        elif cde_model.datatype == "calculated":
            if stored_value == "NaN":
                return ""
            else:
                return stored_value
        else:
            return cde_model.get_display_value(stored_value)

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
