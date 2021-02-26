from collections import OrderedDict
import json

from django.db import ProgrammingError
from django.db import connection

from rdrf.helpers.utils import get_cached_instance
from rdrf.helpers.utils import timed
from rdrf.models.definition.models import Registry, RegistryForm, Section
from rdrf.models.definition.models import CommonDataElement, ClinicalData

from .models import Query
from .models import FieldValue
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
                            errors.append(
                                "columns in sheet %s not all strings: %s" %
                                (sheet_name, column))

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
        try:
            reporting_table_generator.drop_table()
        except Exception as ex:
            logger.error("Report Error: dropping table: %s" % ex)
            raise

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
            logger.exception("Error running explorer query: {}".format(ex))
            raise

    @timed
    def generate_results2(self, reverse_column_map, col_map, max_items):
        from registry.patients.models import Patient
        self.reverse_map = reverse_column_map
        self.col_map = col_map
        report_columns = col_map.values()

        blank_dict = {column_name: None for column_name in report_columns}

        if self.projection:
            self.mongo_models = [model_triple for model_triple in self._get_mongo_fields()]
        else:
            self.mongo_models = []

        sql_only = len(self.mongo_models) == 0

        def get_sql_dict(row):
            sql_columns_dict = {}
            for i, item in enumerate(row):
                sql_column_name = self.reverse_map[i]
                sql_columns_dict[sql_column_name] = item
                sql_columns_dict["snapshot"] = False
            return sql_columns_dict

        def sql_only_c():
            for row in self.cursor:
                d = get_sql_dict(row)
                yield d

        def full_new():
            registry_id = self.registry_model.id
            from copy import copy
            for row in self.cursor:
                row_dict = copy(blank_dict)
                d = get_sql_dict(row)
                row_dict.update(d)
                patient_id = int(d['id'])
                patient_model = Patient.objects.get(id=patient_id)
                q = (FieldValue.objects.filter(registry_id=registry_id)
                     .prefetch_related("patient")
                     .prefetch_related("context")
                     .prefetch_related("form")
                     .prefetch_related("section")
                     .prefetch_related("cde"))

                for context_model in patient_model.context_models:
                    context_id = context_model.pk
                    row = copy(row_dict)
                    row["context_id"] = context_id

                    qry = q.filter(registry_id=registry_id,
                                   patient_id=patient_id,
                                   context_id=context_id,
                                   column_name__in=report_columns,
                                   index__lt=max_items)

                    self._get_fvs_by_datatype(qry, row)

                    yield row

        if self.mongo_search_type == "C":
            # current data - no longitudinal snapshots
            if sql_only:
                for d in sql_only_c():
                    yield d
            else:
                for d in full_new():
                    yield d
        else:
            for d in self.generate_results(reverse_column_map,
                                           col_map,
                                           max_items):
                yield d

    def _get_fvs_by_datatype(self, query, row):
        for fv in query.filter(datatype='string'):
            row[fv.column_name] = fv.raw_value
        for fv in query.filter(datatype='range'):
            row[fv.column_name] = fv.display_value
        for fv in query.filter(datatype='integer'):
            row[fv.column_name] = fv.raw_integer
        for fv in query.filter(datatype='float'):
            row[fv.column_name] = fv.raw_float
        for fv in query.filter(datatype='file'):
            row[fv.column_name] = fv.file_name
        for fv in query.filter(datatype='boolean'):
            row[fv.column_name] = fv.raw_boolean
        for fv in query.filter(datatype='date'):
            row[fv.column_name] = fv.raw_date
        for fv in query.filter(datatype='calculated'):
            row[fv.column_name] = fv.get_calculated_value()

    @timed
    def generate_results(self, reverse_column_map, col_map, max_items):
        self.reverse_map = reverse_column_map
        self.col_map = col_map

        collection = ClinicalData.objects.collection(self.registry_model.code, self.collection)
        history = ClinicalData.objects.collection(self.registry_model.code, "history")

        if self.projection:
            self.mongo_models = [model_triple for model_triple in self._get_mongo_fields()]
        else:
            self.mongo_models = []

        sql_only = len(self.mongo_models) == 0

        def full_c2():
            for row in self.cursor:
                sql_columns_dict = {}
                for i, item in enumerate(row):
                    sql_column_name = self.reverse_map[i]
                    sql_columns_dict[sql_column_name] = item

        def sql_only_c():
            for row in self.cursor:
                sql_columns_dict = {}
                for i, item in enumerate(row):
                    sql_column_name = self.reverse_map[i]
                    sql_columns_dict[sql_column_name] = item
                yield sql_columns_dict

        def full_c():
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

        def longitudinal():
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
                        else:
                            mongo_columns_dict["snapshot"] = True
                            for combined_dict in self._combine_sql_and_mongo(sql_columns_dict, mongo_columns_dict):
                                yield combined_dict

        if self.mongo_search_type == "C":
            # current data - no longitudinal snapshots
            if sql_only:
                for d in sql_only_c():
                    yield d
            else:
                for d in full_c():
                    yield d

        else:
            # include longitudinal ( snapshot) data
            if sql_only:
                for d in sql_only_c():
                    yield d
            else:
                for d in longitudinal():
                    yield d

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
        # [Column(name='id', type_code=23, display_size=None, internal_size=4, precision=None, scale=None, null_ok=None),
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
        cursor = connection.cursor()
        cursor.execute(self.query)
        return cursor

    @timed
    def _get_mongo_metadata(self):
        # TODO not sure why this called multisection_column_map as it contains any
        # selected mongo fields
        data = {"multisection_column_map": OrderedDict()}

        if not self.projection:
            return data

        for cde_dict in self.projection:
            form_model = RegistryForm.objects.get(
                name=cde_dict["formName"], registry=self.registry_model)
            section_model = Section.objects.get(code=cde_dict["sectionCode"])
            cde_model = CommonDataElement.objects.get(code=cde_dict["cdeCode"])
            column_name = self._get_database_column_name(form_model, section_model, cde_model)
            data["multisection_column_map"][(
                form_model, section_model, cde_model)] = column_name
        return data

    def _get_database_column_name(self, form_model, section_model, cde_model):
        return "column_%s_%s_%s" % (form_model.pk,
                                    section_model.pk,
                                    cde_model.pk)

    def _get_mongo_fields(self):
        for cde_dict in self.projection:
            form_model = get_cached_instance(
                RegistryForm,
                name=cde_dict["formName"],
                registry=self.registry_model)
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

    def _process_all_rows(self, collection, max_items=3):

        qry = collection.filter(django_model="Patient")
        # list of clinical data
        data = qry.values('django_id', 'context_id', 'data')
        for item in data:
            result_map = self._get_result_map(item['data'], max_items=max_items)
            result_map['id'] = item['django_id']

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
                                        values.append(
                                            self._get_sensible_value_from_cde(
                                                cde_model, cde_dict["value"]))

                            return values
                        else:
                            for cde_dict in section_dict["cdes"]:
                                if cde_dict["code"] == cde_model.code:
                                    value = self._get_sensible_value_from_cde(
                                        cde_model, cde_dict["value"])
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
        raise NotImplementedError("MongoDB is no longer supported in the RDRF")

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
        """
        Returns all rows from a cursor as a list of dicts
        https://stackoverflow.com/questions/10888844/using-dict-cursor-in-django
        """
        desc = cursor.description
        return [
            dict(zip([col[0] for col in desc], row))
            for row in cursor.fetchall()
        ]


class ParseQuery(object):
    def get_parameters(self):
        pass

    def set_parameters(self):
        pass


def create_field_values(registry_model, patient_model, context_model, remove_existing=False, form_model=None):
    """
    Create faster representations of the clinical data for reporting
    """
    if remove_existing:
        qry = FieldValue.objects.filter(registry=registry_model,
                                        patient=patient_model,
                                        context=context_model)

        if form_model:
            qry = qry.filter(form=form_model)

        qry.delete()

    dynamic_data = patient_model.get_dynamic_data(registry_model,
                                                  context_id=context_model.id)
    if dynamic_data:
        for form_dict in dynamic_data["forms"]:
            try:
                form_model = RegistryForm.objects.get(name=form_dict["name"],
                                                      registry=registry_model)
            except RegistryForm.DoesNotExist:
                continue
            for section_dict in form_dict["sections"]:
                try:
                    section_model = Section.objects.get(code=section_dict["code"])
                except Section.DoesNotExist:
                    continue
                if not section_dict["allow_multiple"]:
                    for cde_dict in section_dict["cdes"]:
                        try:
                            cde_model = CommonDataElement.objects.get(code=cde_dict["code"])
                        except CommonDataElement.DoesNotExist:
                            continue

                        FieldValue.put(registry_model,
                                       patient_model,
                                       context_model,
                                       form_model,
                                       section_model,
                                       cde_model,
                                       0,
                                       cde_dict["value"])
                else:
                    for index, item in enumerate(section_dict["cdes"]):
                        for cde_dict in item:
                            try:
                                cde_model = CommonDataElement.objects.get(code=cde_dict["code"])
                            except CommonDataElement.DoesNotExist:
                                continue

                            FieldValue.put(registry_model,
                                           patient_model,
                                           context_model,
                                           form_model,
                                           section_model,
                                           cde_model,
                                           index,
                                           cde_dict["value"])
