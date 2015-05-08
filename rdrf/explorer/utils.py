import re
import json
import ast

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from django.db import ProgrammingError
from django.db import connection

from models import Query

from explorer import app_settings
from rdrf.utils import mongo_db_name_reg_id
from models import Query
from forms import QueryForm

class DatabaseUtils(object):

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
        except ConnectionFailure, e:
            return False, e
    
    def run_sql(self):
        try:
            cursor = connection.cursor()
            self.cursor = cursor.execute(self.query)
            self.result = self._dictfetchall(cursor)
        except ProgrammingError as error:
            self.result = {'error_msg': error.message}

        return self

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
                aggregation.append({ key:value })

        django_ids = []
        if self.result:
            for r in self.result:
                django_ids.append(r["id"])

        records = []
        if mongo_search_type == 'F':
            criteria["django_id"] = {"$in":django_ids}
            results = collection.find(criteria, projection)
        elif mongo_search_type == 'A':
            if "$match" in aggregation:
                aggregation["$match"].update({"django_id":{"$in":django_ids }})
            else:
                aggregation.append({"$match": {"django_id":{"$in":django_ids }} })
            results = collection.aggregate(aggregation)
            results = results['result']

        for cur in results:
            row = {}
            for k in cur:
                raise Exception(k)
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
        return MongoClient(app_settings.VIEWER_MONGO_HOST,
                           app_settings.VIEWER_MONGO_PORT)


class ParseQuery(object):

    def get_parameters(query):
        pass
    
    def set_parameters(query):
        pass
