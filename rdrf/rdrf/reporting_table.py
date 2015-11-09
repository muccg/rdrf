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
                "calculated": alc.Float,
                "integer": alc.Integer,
                "int": alc.Integer,
                "string": alc.String,
                }

    def __init__(self, user, registry_model, type_overrides={}):
        self.user = user
        self.counter = 0
        self.col_map = {}
        self.registry_model = registry_model
        self.type_overrides = type_overrides
        self.engine = self._create_engine()
        self.columns = set([])
        self.table = None

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
        return create_engine(connection_string)

    def create_table(self):
        self.table.create()
        logger.debug("created table based on schema")

    def drop_table(self):
        if self.table is not None:
            self.table.drop(self.engine)

    def create_columns(self, sql_metadata, mongo_metadata):
        self.columns = set([])
        self.columns.add(self._create_column("context_id", alc.Integer))

        for column_metadata in sql_metadata:
            column_from_sql = self._create_column_from_sql(column_metadata)
            self.columns.add(column_from_sql)

        for form_model, section_model, cde_model in mongo_metadata["column_map"]:
            column_name = mongo_metadata["column_map"][(form_model, section_model, cde_model)]
            column_from_mongo = self._create_column_from_mongo(column_name, cde_model)
            self.columns.add(column_from_mongo)

    def _create_column_from_sql(self, column_metadata):
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

        return self._create_column(column_name, datatype)

    def _create_column_from_mongo(self, column_name, cde_model):
        column_data_type = self._get_sql_alchemy_datatype(cde_model)
        return self._create_column(column_name, column_data_type)

    def run_explorer_query(self, explorer_query):
        self.create_table()
        for result_dict in explorer_query.generate_results():
            self.insert_row(result_dict)

    # the methods below dump everything

    def insert_patient_contexts(self, patient_model):
        self.create_table()
        for context_dict in self._get_context_dicts(patient_model):
            self.insert_row(context_dict)

    def insert_row(self, value_dict):
        # each row will be a denormalised section item
        logger.debug("inserting context dict: %s" % value_dict)
        self.engine.execute(self.table.insert().values(**value_dict))

    def _create_column(self, name, datatype=alc.String):
        short_name = "col%s" % self.counter
        self.counter += 1
        column = alc.Column(short_name, datatype, nullable=True)
        self.columns.add(column)
        self.col_map[name] = short_name
        logger.debug("columns %s --> %s" % (short_name, name))
        return column

    #   get rid of stuff below

    def _get_context_dicts(self, patient_model):
        id = patient_model.pk
        context_dicts = {}

        for context_id, form_name, section_code, field, value in self._get_data(patient_model):
            if context_id not in context_dicts:
                context_dict = {}
                context_dict[self.col_map['id']] = id
                context_dict[self.col_map['context_id']] = context_id
                context_dicts[context_id] = context_dict
            else:
                context_dict = context_dicts[context_id]

            delimited_name = self._get_delimited_name(form_name, section_code, field)
            column_name = self.col_map[delimited_name]
            logger.debug("%s is %s = %s" % (column_name, delimited_name, value))
            context_dict[column_name] = value

        for context_id in context_dicts:
            yield context_dicts[context_id]

    def _get_column_name(self, form_name, section_code, field):
        delimited_name = self._get_delimited_name(form_name, section_code, field)
        col = "col%s" % self.counter
        self.col_map[delimited_name] = col
        self.counter += 1

        return col

    def _get_delimited_name(self, form_name, section_code, cde_code):
        f = form_name.replace(" ", "")
        return "%s_%s_%s" % (f, section_code, cde_code)

    def _get_data(self, patient_model):
        """
        :param patient_model:
        :return: a generator that yields form_name, section_code, cde_code, cde_value tuples
        """
        form_name = "Demographics"
        context_id = None   # dummy really
        for field, section, column_datatype in self.DEMOGRAPHIC_FIELDS:
            value = getattr(patient_model, field)
            yield context_id, form_name, section, field, value

        mongo_data = DynamicDataWrapper(patient_model).load_dynamic_data(self.registry_model.code,
                                                                         "cdes",
                                                                         flattened=False)
        if isinstance(mongo_data, dict):
            self._process_form_dict(mongo_data)
        else:
            for form_dict in mongo_data:
                self._process_form_dict(form_dict)

    def _process_form_dict(self, form_dict):
        context_id = mongo_data.get("context_id", None)
        for form_dict in mongo_data["forms"]:
            form_name = form_dict["name"]
            for section_dict in form_dict["sections"]:
                section = section_dict["code"]
                if section_dict["allow_multiple"]:
                    for section_item in section_dict["cdes"]:
                        for cde_dict in section_item:
                            field = cde_dict["code"]
                            value = cde_dict["value"]
                            yield context_id, form_name, section, field, value
                else:
                    for cde_dict in section_dict["cdes"]:
                        field = cde_dict["code"]
                        value = cde_dict["value"]
                        yield context_id, form_name, section, field, value

    def _cde_name(self, form_model, section_model, cde_model):
        form_name = form_model.name.replace(" ", "")
        return "%s_%s_%s" % (form_name, section_model.code, cde_model.code)

    def create_schema(self):
        logger.debug("creating table schema")
        logger.debug("There are %s columns" % len(self.columns))
        table_name = self._generate_temporary_table_name()
        logger.debug("table name will be = %s" % table_name)
        self.table = alc.Table(table_name, MetaData(self.engine), *self.columns, schema=None)

    def _generate_temporary_table_name(self):
        return "reporting_table"

    def _get_sql_alchemy_datatype(self, cde_model):
        if cde_model.code in self.type_overrides:
            datatype = self.type_overrides[cde_model.code]
        else:
            datatype = cde_model.datatype

        return self.TYPE_MAP.get(datatype, alc.String)

    def _get_sql_alchemy_datatype_from_sql_cursor_column_info(self, column_info):
        oid = column_info.oid
        type_code = column_info.type_code


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
            value_dict["formName"] = form_model.name
            value_dict["sectionCode"] = section_model.code
            value_dict["cdeCode"] = cde_model.code
            value_dict["value"] = True  # we only need to store the true / checked cdes

            projected_cdes.append(value_dict)


        logger.debug("projected cdes = %s" % projected_cdes)
        return json.dumps(projected_cdes)




