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
from models import Query
from forms import QueryForm


class MissingDataError(Exception):
    pass



class DatabaseUtils(object):

    result = None

    def __init__(self, form_object=None, verify=False):
        if form_object and isinstance(form_object, QueryForm):
            self.form_object = form_object
            self.query = form_object['sql_query'].value()
            self.regsitry_id = self.form_object['registry'].value()
            if not verify:
                self.collection = self.form_object['collection'].value()
                self.criteria = self._string_to_json(self.form_object['criteria'].value())
                self.projection = self._string_to_json(self.form_object['projection'].value())
                self.aggregation = self.form_object['aggregation'].value()
                self.mongo_search_type = self.form_object['mongo_search_type'].value()
        elif form_object and isinstance(form_object, Query):
            self.form_object = form_object
            self.query = form_object.sql_query
            self.regsitry_id = self.form_object.registry.id
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
        cursor = self.create_cursor()
        sql_metadata = self._get_sql_metadata(cursor)
        mongo_metadata = self._get_mongo_metadata()
        reporting_table_generator.create_schema(sql_metadata, mongo_metadata)
        reporting_table_generator.run_explorer_query(self)

    def generate_results(self):
        self.mongo_client = self._get_mongo_client()
        self.database = self.mongo_client[mongo_db_name_reg_id(self.regsitry_id)]
        collection = self.database[self.collection]

        for row in self.cursor:
            for mongo_result in self.run_mongo_one_row(row, collection):
                yield self._combine_sql_and_mongo(row, mongo_result)

    def _combine_sql_and_mongo(self, sql_result, mongo_result):
        combined = {}
        combined.update(sql_result)
        combined.update(mongo_result)
        return combined

    def create_cursor(self):
        cursor = connection.cursor()
        self.cursor = cursor.execute(self.query)
        self.sql_column_metadata = self._get_sql_column_metadata(cursor)
        return self.cursor

    def _get_sql_metadata(self, cursor):
        return [item for item in cursor.description]

    def _get_mongo_metadata(self):
        import json
        from rdrf.models import Registry, RegistryForm, Section, CommonDataElement
        from rdrf.utils import forms_and_sections_containing_cde

        def short__column_name(form_model, section_model, cde_code):
            return form_model.name[:5] + "_" + section_model.code + "_" + cde_model.code

        registry_model = Registry.objects.get(pk=self.regisitry_id)
        data = {"column_map": {}}

        # list of dictionaries like :  {"form": <formname>, "section": <sectioncode>, "cde": <cdecode>}
        cde_dicts = json.loads(self.projection)
        for cde_dict in cde_dicts:
            form_model = RegistryForm.objects.get(name=cde_dict["form"])
            section_model = Section.objects.get(code=cde_dict["section"])
            cde_model = CommonDataElement.objects.get(code=cde_dict["cde"])
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
                data["column_map"][(form_model, section_model, cde_model)] = short_column_name(form_model,
                                                                                              section_model,
                                                                                              cde_model)

        return data


    def _inspect_cursor(self, cursor):
        raise Exception(cursor)

    def run_mongo_one_row(self, sql_row, mongo_collection):
        django_model = sql_row.get("django_model", "Patient")
        django_id = sql_row["id"]
        mongo_query = {"django_model": django_model,
                       "django_id": django_id}
        for mongo_document in mongo_collection.find(mongo_query):
            result = {}
            result["context_id"] = mongo_document.get("context_id", None)
            for form_model, section_model, cde_model in self._get_mongo_fields():
                short_namre
                result[short_name] = self._get_cde_value(form_model,
                                                         section_model,
                                                         cde_model,
                                                         mongo_document)
            yield result



    def _get_cde_value(self, form_model, section_model, cde_model, mongo_document):
        for form_dict in mongo_document["forms"]:
            if form_dict["name"] == form_model.name:
                for section_dict in form_dict["sections"]:
                    if section_dict["code"] == section_model.code:
                        if section_dict["allow_multiple"]:
                            values = []
                            for section_item in section_dict["cdes"]:
                                for cde_dict in section_item:
                                    if cde_dict["code"] == cde_model.code:
                                        values.append(cde_dict["value"])
                            return values
                    else:
                        for cde_dict in section_dict["cdes"]:
                            if cde_dict["code"] == cde_model["code"]:
                                return cde_dict["value"]

    def run_mongo(self):
        client = self._get_mongo_client()

        projection = {}
        criteria = {}

        database = client[mongo_db_name_reg_id(self.regsitry_id)]
        collection = database[self.collection]

        mongo_search_type = self.mongo_search_type

        criteria = self.criteria
        projection = self.projection

        aggregation = []

        pipline = self.aggregation.split("|")
        for pipe in pipline:
            for key, value in ast.literal_eval(pipe).iteritems():
                aggregation.append({key: value})

        django_ids = []
        if self.result:
            for r in self.result:
                django_ids.append(r["id"])

        records = []
        if mongo_search_type == 'F':
            criteria["django_id"] = {"$in": django_ids}
            results = collection.find(criteria, projection)
        elif mongo_search_type == 'A':
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
