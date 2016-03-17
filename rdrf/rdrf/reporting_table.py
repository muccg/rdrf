import sqlalchemy as alc
from sqlalchemy import create_engine, MetaData
from rdrf.dynamic_data import DynamicDataWrapper
import explorer
from explorer.utils import DatabaseUtils

import logging
logger = logging.getLogger("registry_log")

from django.conf import settings


class ReportingTableGenerator(object):
    DEMOGRAPHIC_FIELDS = [('family_name', 'todo', alc.String),
                          ('given_names', 'todo', alc.String),
                          ('home_phone', 'todo', alc.String),
                          ('email', 'todo', alc.String)]
    TYPE_MAP = {"float": alc.Float,
                "calculated": alc.String, #todo fix this - some calculated field are strings some numbers
                "integer": alc.Integer,
                "int": alc.Integer,
                "string": alc.String,
                }

    def __init__(self, user, registry_model, multisection_unroller, humaniser, type_overrides={}):
        self.user = user
        self.counter = 0
        self.col_map = {}
        self.registry_model = registry_model
        self.type_overrides = type_overrides
        self.engine = self._create_engine()
        self.columns = set([])
        self.table_name = ""
        self.table = None
        self.reverse_map = {}
        self.multisection_column_map = {}
        self.multisection_unroller = multisection_unroller
        self.humaniser = humaniser

    def _create_engine(self):
        report_db_data = settings.DATABASES["reporting"]
        db_user = report_db_data["USER"]
        db_pass = report_db_data["PASSWORD"]
        database = report_db_data["NAME"]
        host = report_db_data["HOST"]
        port = report_db_data["PORT"]
        connection_string = "postgresql://{0}:{1}@{2}:{3}/{4}".format(db_user,
                                                                      db_pass,
                                                                      host,
                                                                      port,
                                                                      database)

        logger.debug("connection_string = %s" % connection_string)
        return create_engine(connection_string)

    def create_table(self):
        self.table.create()
        logger.debug("created table based on schema")

    def drop_table(self):
        drop_table_sql = "DROP TABLE %s" % self.table_name
        conn = self.engine.connect()
        try:
            conn.execute(drop_table_sql)
            logger.debug("dropped temp table %s" % self.table_name)
        except:
            pass
        conn.close()

    def set_table_name(self, obj):
        logger.debug("setting table name from %s %s" % (self.user.username, obj))
        t = "report_%s_%s" % (obj.id, self.user.pk)
        self.table_name = t
        logger.info("table name = %s" % self.table_name)

    def _add_reverse_mapping(self, key, value):
        self.reverse_map[key] = value
        logger.debug("reverse map %s --> %s" % (key, value))

    def create_columns(self, sql_metadata, mongo_metadata):
        logger.debug("creating columns from sql and mongo metadata")
        self.columns = set([])
        self.columns.add(self._create_column("context_id", alc.Integer))
        # These columns will always appear
        self._add_reverse_mapping("context_id", "context_id")

        self.columns.add(self._create_column("timestamp", alc.String))
        self._add_reverse_mapping("timestamp", "timestamp")

        self.columns.add(self._create_column("snapshot", alc.Boolean))
        self._add_reverse_mapping("snapshot", "snapshot")

        for i, column_metadata in enumerate(sql_metadata):
            column_from_sql = self._create_column_from_sql(column_metadata)
            self.columns.add(column_from_sql)
            #to get from tuple
            # map the column's index in tuple to the column name in the dict
            self._add_reverse_mapping(i, column_metadata["name"])

        for form_model, section_model, cde_model in mongo_metadata["multisection_column_map"]:
            column_name = mongo_metadata["multisection_column_map"][(form_model, section_model, cde_model)]
            column_from_mongo = self._create_column_from_mongo(column_name, form_model, section_model, cde_model)
            self.columns.add(column_from_mongo)

    def _create_column_from_sql(self, column_metadata):
        logger.debug("column metadata = %s" % column_metadata)
        column_name = column_metadata["name"]
        type_name = column_metadata["type_name"]
        # Not sure if this good idea ...
        # these type_names are coming from introspection on the sql cursor
        if type_name == "varchar":
            datatype = alc.String
        elif type_name == "bool":
            datatype = alc.Boolean
        elif "float" in type_name:
            datatype = alc.FLOAT
        elif "int" in type_name:
            datatype = alc.INTEGER
        elif "date" in type_name:
            datatype = alc.DATE
        else:
            datatype = alc.String

        logger.debug("mapped sql alc data type = %s" % datatype)
        return self._create_column(column_name, datatype)

    def _create_column_from_mongo(self, column_name, form_model, section_model, cde_model):
        column_data_type = self._get_sql_alchemy_datatype(cde_model)
        self._add_reverse_mapping((form_model, section_model, cde_model), column_name)
        if section_model.allow_multiple:
            # This map is used when we unroll/"denormalise" the multisection data
            logger.debug("multisection_column_map = %s" % self.multisection_column_map)
            if section_model.code in self.multisection_column_map:
                self.multisection_column_map[section_model.code].append(column_name)
            else:
                self.multisection_column_map[section_model.code] = [column_name]

        return self._create_column(column_name, column_data_type)

    def run_explorer_query(self, database_utils):
        self.create_table()
        self.multisection_unroller.multisection_column_map = self.multisection_column_map
        errors = 0
        for result_dict in database_utils.generate_results(self.reverse_map):
            for unrolled_row in self.multisection_unroller.unroll(result_dict):
                try:
                    self.insert_row(unrolled_row)
                except Exception, ex:
                    errors += 1
                    logger.error("report error: query %s row %s error: %s" % (database_utils.form_object.title,
                                                                              unrolled_row,
                                                                              ex))
        logger.info("query errors: %s" % errors)

    def insert_row(self, value_dict):
        # each row will be a denormalised section item
        logger.debug("inserting context dict: %s" % value_dict)
        self.engine.execute(self.table.insert().values(**value_dict))

    def _create_column(self, name, datatype=alc.String):
        column = alc.Column(name, datatype, nullable=True)
        self.columns.add(column)
        logger.debug("added column %s type %s" % (name, datatype))
        return column

    def create_schema(self):
        self.drop_table()
        logger.debug("creating table schema")
        logger.debug("There are %s columns" % len(self.columns))
        logger.debug("table name will be = %s" % self.table_name)
        self.table = alc.Table(self.table_name, MetaData(self.engine), *self.columns, schema=None)

    def _generate_temporary_table_name(self):
        return "reporting_table" + self.user.username

    def _get_sql_alchemy_datatype(self, cde_model):
        if cde_model.code in self.type_overrides:
            datatype = self.type_overrides[cde_model.code]
        else:
            datatype = cde_model.datatype

        return self.TYPE_MAP.get(datatype, alc.String)

    def dump_csv(self, stream):
        import csv
        writer = csv.writer(stream)
        select_query = alc.sql.select([self.table])
        db_connection = self.engine.connect()
        result = db_connection.execute(select_query)
        writer.writerow(result.keys())
        writer.writerows(result)
        db_connection.close()
        return stream


class MongoFieldSelector(object):
    def __init__(self, user, registry_model, query_model, checkbox_ids=[]):
        if checkbox_ids is not None:
            self.checkbox_ids = checkbox_ids
        else:
            self.checkbox_ids = []

        self.user = user
        self.registry_model = registry_model
        self.query_model = query_model
        if self.query_model:
            self.existing_data = self._get_existing_report_choices(self.query_model)
        else:
            self.existing_data = {}

    def _get_existing_report_choices(self, query_model):
        import json
        try:
            return json.loads(query_model.projection)
        except:
            return []


    @property
    def field_data(self):
        return {"fields": self.fields}

    @property
    def fields(self):
        self.field_info = []
        for form_model in self.registry_model.forms:
            if self.user.can_view(form_model) and not form_model.is_questionnaire:
                for section_model in form_model.section_models:
                    for cde_model in section_model.cde_models:
                        self._get_field_info(form_model, section_model, cde_model)

        return self.field_info

    def _get_saved_value(self, form_model, section_model, cde_model):
        for value_dict in self.existing_data:
            if value_dict["formName"] == form_model.name:
                if value_dict["sectionCode"] == section_model.code:
                    if value_dict["cdeCode"] == cde_model.code:
                        return value_dict["value"]
        return False

    def _get_field_info(self, form_model, section_model, cde_model):
        saved_value = self._get_saved_value(form_model, section_model, cde_model)
        field_id = "cb_%s_%s_%s_%s" % (self.registry_model.code,
                                       form_model.pk,
                                       section_model.pk,
                                       cde_model.pk)
        field_label = cde_model.name
        self.field_info.append({"form": form_model.name,
                                "sectionCode": section_model.code,
                                "sectionName": section_model.display_name,
                                "cdeCode": cde_model.code,
                                "id": field_id,
                                "label": field_label,
                                "savedValue": saved_value})

    @property
    def projections_json(self):
        # this method returns the new projection data back to the client based
        # on the list of checked items passed in
        # the constructed json is independent of db ids ( as these will change
        # is import of registry definition occurs
        import json
        from rdrf.models import Registry, RegistryForm, Section, CommonDataElement
        projected_cdes = []
        for checkbox_id in self.checkbox_ids:
            # <input type="checkbox" name="cb_fh_39_104_CarotidUltrasonography" id="cb_fh_39_104_CarotidUltrasonography">
            # registry code, form pk, section pk, cde_code
            # cb_fh_39_105_EchocardiogramResult
            _, registry_code, form_pk, section_pk, cde_code = checkbox_id.split("_")

            form_model = RegistryForm.objects.get(pk=int(form_pk))
            section_model = Section.objects.get(pk=int(section_pk))
            cde_model = CommonDataElement.objects.get(code=cde_code)

            value_dict = {}
            value_dict["registryCode"] = form_model.registry.code
            value_dict["formName"] = form_model.name
            value_dict["sectionCode"] = section_model.code
            value_dict["cdeCode"] = cde_model.code
            value_dict["value"] = True  # we only need to store the true / checked cdes

            projected_cdes.append(value_dict)

        logger.debug("projected cdes = %s" % projected_cdes)
        return json.dumps(projected_cdes)
