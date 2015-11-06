import sqlalchemy as alc
from sqlalchemy import create_engine, MetaData
from rdrf.dynamic_data import DynamicDataWrapper
from utils import DatabaseUtils

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

    def create_schema(self, sql_metadata, mongo_metadata):
        self.columns = set([])
        for column_metadata in sql_metadata:
            column_from_sql = self._create_column_from_sql(column_metadata)
            columns.add(column_from_sql)

        for form_model, section_model, cde_model in mongo_metadata["column_map"]:
            column_name = mongo_metadata["column_map"][(form_model, section_model, cde_model)]
            column_from_mongo = self._create_column_from_mongo(column_name, cde_model)
            columns.add(column_from_mongo)

        self._create_schema()

    def _create_column_from_sql(self, column_metadata):
        pass

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

    def _create_schema(self):
        cdes = []
        viewable_forms = []
        for form_model in self.registry_model.forms:
            if self.user.can_view(form_model) and not form_model.is_questionnaire:
                viewable_forms.append(form_model)

        for form_model in viewable_forms:
            for section_model in form_model.section_models:
                for cde_model in section_model.cde_models:
                    cde_data = (form_model, section_model, cde_model)
                    cdes.append(cde_data)

        table_name = self._generate_temporary_table_name()

        patient_id_column = self._create_column("id", alc.Integer)
        context_id_column = self._create_column("context_id", alc.Integer)

        for field, section,  column_type in self.DEMOGRAPHIC_FIELDS:
            column_name = self._get_delimited_name("Demographics", section, field)
            self._create_column(column_name, column_type)

        # TODO need to add demographics columns, consents , registry specific fields ...

        for form_model, section_model, cde_model in cdes:
            column_name = self._get_delimited_name(form_model.name, section_model.code, cde_model.code)
            column_datatype = self._get_sql_alchemy_datatype(cde_model)
            self._create_column(column_name, column_datatype)

        return alc.Table(table_name, MetaData(self.engine), *self.columns, schema=None)

    def _generate_temporary_table_name(self):
        return "reporting_table"

    def _get_sql_alchemy_datatype(self, cde_model):
        if cde_model.code in self.type_overrides:
            datatype = self.type_overrides[cde_model.code]
        else:
            datatype = cde_model.datatype

        return self.TYPE_MAP.get(datatype, alc.String)













































