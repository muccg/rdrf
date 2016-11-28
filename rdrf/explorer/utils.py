from collections import OrderedDict
import json
import ast

from django.db import ProgrammingError
from django.db import connection

from rdrf.utils import get_cached_instance
from rdrf.utils import timed
from rdrf.models import Registry, RegistryForm, Section
from rdrf.models import CommonDataElement, Modjgo

from .models import Query
from .forms import QueryForm

import logging
logger = logging.getLogger(__name__)


class MissingDataError(Exception):
    pass


class DatabaseUtils(object):

    result = None

    def __init__(self, form_object=None, verify=False):
        self.error_messages = []
        self.warning_messages = []

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

    def run_sql(self):
        try:
            cursor = self.create_cursor()
            self.result = self._dictfetchall(cursor)
        except ProgrammingError as error:
            self.result = {'error_msg': str(error)}

        return self

    def validate_mixed_query(self):
        # not really parsing -
        errors = []
        if hasattr(self, "query") and self.query.mongo_search_type == "M":
            import json
            try:
                data = json.loads(self.query.sql_query)
                static_sheets = data["static_sheets"]
                for sheet in static_sheets:
                    sheet_name = sheet["name"]
                    columns = sheet["columns"]
                    for column in columns:
                        if not isinstance(column, str):
                            errors.append("columns in sheet %s not all strings: %s" % (sheet_name, column))

            except ValueError as ve:
                errors.append("JSON malformed: %s" % ve)
            except KeyError as ke:
                errors.append("key error: %s" % ke)

            if len(errors) > 0:
                self.result = {'error_msg': ','.join(errors)}
                return self
            else:
                # client assumed a dict made from cursor - not sure what to put here
                self.result = {}
                return self
        else:
            return self

    @timed
    def dump_results_into_reportingdb(self, reporting_table_generator):
        logger.debug("*********** running query and dumping to temporary table *******")
        try:
            reporting_table_generator.drop_table()
        except Exception as ex:
            logger.error("Report Error: dropping table: %s" % ex)
            raise

        logger.debug("dropped temporary table")

        try:
            self.cursor = self.create_cursor()
        except Exception as ex:
            logger.error("Report Error: create cursor: %s" % ex)
            raise

        try:
            sql_metadata = self._get_sql_metadata(self.cursor)
        except Exception as ex:
            logger.error("Report Error: getting sql metadata: %s" % ex)
            raise

        try:
            mongo_metadata = self._get_mongo_metadata()
        except Exception as ex:
            logger.error("Report Error: getting mongo metadata: %s" % ex)
            raise

        try:
            reporting_table_generator.create_columns(sql_metadata, mongo_metadata)
        except Exception as ex:
            logger.error("Report Error: creating columns: %s" % ex)
            raise

        try:
            reporting_table_generator.create_schema()
        except Exception as ex:
            logger.error("Report Error: creating schema: %s" % ex)
            raise

        try:
            return reporting_table_generator.run_explorer_query(self)
        except Exception as ex:
            logger.exception("Error running explorer query: %s")
            raise

    @timed
    def generate_results(self, reverse_column_map, col_map, max_items):
        logger.debug("generate_results ...")
        self.reverse_map = reverse_column_map
        self.col_map = col_map

        collection = Modjgo.objects.collection(self.registry_model.code, self.collection)
        history = Modjgo.objects.collection(self.registry_model.code, "history")

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
                logger.debug("processing sql row ..")
                sql_columns_dict = {}
                for i, item in enumerate(row):
                    sql_column_name = self.reverse_map[i]
                    sql_columns_dict[sql_column_name] = item

                logger.debug("created sql dict")

                # A mongo record may not exist ( represented as None )
                for mongo_columns_dict in self.run_mongo_one_row(sql_columns_dict, collection, max_items):
                    if mongo_columns_dict is None:
                        logger.debug("no mongo data - yield sql only")
                        sql_columns_dict["snapshot"] = False
                        yield sql_columns_dict
                    else:
                        logger.debug("mongo data exists")
                        mongo_columns_dict["snapshot"] = False
                        logger.debug("marked row as not a snapshot")
                        for combined_dict in self._combine_sql_and_mongo(sql_columns_dict, mongo_columns_dict):
                            logger.debug("yielding combined dict")
                            if combined_dict is None:
                                logger.debug("combined dict is None ???")

                            logger.debug("combined_dict = %s" % combined_dict)
                            yield combined_dict
        else:
            # include longitudinal ( snapshot) data
            logger.debug("LONGITUDINAL MONGO REPORT")
            for row in self.cursor:
                sql_columns_dict = {}
                for i, item in enumerate(row):
                    sql_column_name = self.reverse_map[i]
                    sql_columns_dict[sql_column_name] = item

                for mongo_columns_dict in self.run_mongo_one_row(sql_columns_dict, collection, max_items):
                    if mongo_columns_dict is None:
                        sql_columns_dict["snapshot"] = False
                        yield sql_columns_dict
                    else:
                        mongo_columns_dict["snapshot"] = False
                        for combined_dict in self._combine_sql_and_mongo(sql_columns_dict, mongo_columns_dict):
                            yield combined_dict

                for mongo_columns_dict in self.run_mongo_one_row_longitudinal(
                        sql_columns_dict, history, max_items):
                    if mongo_columns_dict is None:
                        yield None

                    mongo_columns_dict["snapshot"] = True
                    for combined_dict in self._combine_sql_and_mongo(sql_columns_dict, mongo_columns_dict):
                        yield combined_dict

    def _combine_sql_and_mongo(self, sql_result_dict, mongo_result_dict):
        combined_dict = {}
        combined_dict.update(sql_result_dict)
        combined_dict.update(mongo_result_dict)
        yield combined_dict

    def _get_sql_type_info(self):
        # reporting=# select oid, typname,typcategory from pg_type;;
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
        # type_code is looked up in the oid map
        # cursor description gives list:
        #[Column(name='id', type_code=23, display_size=None, internal_size=4, precision=None, scale=None, null_ok=None),
        # Column(name='family_name', type_code=1043, display_size=None, internal_size=100, precision=None, scale=None, null_ok=None),
        # Column(name='given_names', type_code=1043, display_size=None,
        # internal_size=100, precision=None, scale=None, null_ok=None),
        # Column(name='date_of_birth', type_code=1082, display_size=None,
        # internal_size=4, precision=None, scale=None, null_ok=None),
        # Column(name='Working Group', type_code=1043, display_size=None,
        # internal_size=100, precision=None, scale=None, null_ok=None)]

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
        # TODO not sure why this called multisection_column_map as it contains any selected mongo fields
        data = {"multisection_column_map": OrderedDict()}

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

    def run_mongo_one_row(self, sql_column_data, collection, max_items):
        mongo_query = {
            "django_model": "Patient",
            "django_id": sql_column_data["id"],  # convention?
        }

        records = collection.find(**mongo_query).data()
        num_records = records.count()
        if num_records == 0:
            yield None
        else:
            for mongo_document in records:
                yield self._get_result_map(mongo_document, max_items=max_items)

    def _get_result_map(self, mongo_document, is_snapshot=False, max_items=3):
        result = {}
        if is_snapshot:
            # snapshots copy entire patient record into record field
            record = mongo_document["record"]
        else:
            record = mongo_document
        result["context_id"] = record.get("context_id", None)

        # timestamp from top level in for current and snapshot
        result['timestamp'] = mongo_document.get("timestamp", None)

        for key, column_name in self.col_map.items():
            if isinstance(key, tuple):
                if len(key) == 4:
                    # NB section index is 1 based in report
                    form_model, section_model, cde_model, section_index = key
                else:
                    raise Exception("report key error: %s" % key)

            else:
                continue

            if section_model.allow_multiple:
                values = self._get_cde_value(form_model,
                                             section_model,
                                             cde_model,

                                             record)

                if len(values) > max_items:
                    self.warning_messages.append(
                        "%s %s has more than %s items in the section" %
                        (form_model.name, section_model.display_name, max_items))

                try:
                    result[column_name] = values[section_index - 1]
                except IndexError:
                    result[column_name] = None

            else:
                value = self._get_cde_value(form_model,
                                            section_model,
                                            cde_model,
                                            record)
                result[column_name] = value
        return result

    def run_mongo_one_row_longitudinal(self, sql_column_data, history, max_items):
        mongo_query = {"django_id": sql_column_data["id"],
                       "django_model": "Patient",
                       "record_type": "snapshot"}
        for snapshot in history.find(**mongo_query).data():
            yield self._get_result_map(snapshot, is_snapshot=True, max_items=max_items)

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
        datatype = cde_model.datatype.strip().lower()
        if datatype == "calculated" and stored_value == "NaN":
            return None
        if datatype != 'string' and stored_value in ['', ' ', None]:
            # ensure we don't pass empty string back for numeric fields.
            # range fields will always be non-blank, non-whitespace
            return None
        if datatype == "file":
            return "FILE"
        return cde_model.get_display_value(stored_value)

    def run_mongo(self):
        projection = {}
        criteria = {}
        raise NotImplementedError("fixme")
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
                    for key, value in cur[k].items():
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


class ParseQuery(object):

    def get_parameters(query):
        pass

    def set_parameters(query):
        pass
