import sqlalchemy as alc
from sqlalchemy import create_engine, MetaData
from rdrf.helpers.utils import timed
from datetime import datetime
from django.conf import settings

import logging
logger = logging.getLogger(__name__)


def temporary_table_name(query_model, user):
    return "report_%s_%s" % (query_model.id, user.pk)


def pg_uri(db):
    "PostgreSQL connection URI for a django database settings dict"
    user = db.get("USER")
    password = db.get("PASSWORD")
    name = db.get("NAME", "")
    host = db.get("HOST")
    port = db.get("PORT")
    userpass = "".join([user, ":" + password if password else "", "@"])
    return "".join(["postgresql://", userpass if user else "",
                    host, ":" + port if port else "", "/", name])


class ColumnLabeller(object):

    def get_label(self, column_name):
        s = self._get_label(column_name)

        return s.upper()

    def _get_label(self, column_name):
        # relies on the encoding of the column names
        from rdrf.models.definition.models import RegistryForm, Section, CommonDataElement
        try:
            column_tuple = column_name.split("_")
            num_parts = len(column_tuple)

            if num_parts == 4:
                dontcare, form_pk, section_pk, cde_code = column_name.split(
                    "_")
                column_index = ""
            elif num_parts == 5:
                dontcare, form_pk, section_pk, cde_code, column_index = column_name.split(
                    "_")
            elif num_parts == 1:
                # non clinical field
                return self._get_sql_field_label(column_name)
            else:
                return column_name

            form_model = RegistryForm.objects.get(pk=int(form_pk))
            section_model = Section.objects.get(pk=int(section_pk))
            cde_model = CommonDataElement.objects.get(code=cde_code)
            if column_index:
                s = form_model.name[:3] + "_" + section_model.display_name[
                    :3] + "_" + cde_model.name[:30] + "_" + column_index
            else:
                s = form_model.name[
                    :3] + "_" + section_model.display_name[:3] + "_" + cde_model.name[:30]

            return s

        except Exception:
            return column_name

    def _get_sql_field_label(self, field_name):
        # we can try to second guess here but these names come from the sql query so can be named
        # by report author anyway
        return field_name


class ReportingTableGenerator(object):
    DEMOGRAPHIC_FIELDS = [('family_name', 'todo', alc.String),
                          ('given_names', 'todo', alc.String),
                          ('home_phone', 'todo', alc.String),
                          ('email', 'todo', alc.String)]
    TYPE_MAP = {"float": alc.Float,
                # todo fix this - some calculated field are strings some
                # numbers
                "calculated": alc.String,
                "integer": alc.Integer,
                "Integer": alc.Integer,
                "int": alc.Integer,
                "string": alc.String,
                "date": alc.Date,
                "range": alc.String,
                "file": alc.String,
                }

    def __init__(
            self,
            user,
            registry_model,
            multisection_handler,
            humaniser,
            type_overrides={},
            max_items=3):
        self.user = user
        self.col_map = {}
        self.registry_model = registry_model
        self.type_overrides = type_overrides
        self.engine = self._create_engine()
        self.columns = set([])
        self.column_names = []
        self.table_name = ""
        self.table = None
        self.reverse_map = {}
        self.multisection_handler = multisection_handler
        self.humaniser = humaniser
        self.max_items = max_items
        self.column_labeller = ColumnLabeller()

        self.error_messages = []
        self.warning_messages = []

    def _create_engine(self):
        return create_engine(pg_uri(settings.DATABASES["default"]))

    @timed
    def create_table(self):
        self.table.create()

    def _get_blank_row(self):
        return {column_name: None for column_name in self.column_names}

    @timed
    def drop_table(self):
        drop_table_sql = "DROP TABLE %s" % self.table_name
        conn = self.engine.connect()
        try:
            conn.execute(drop_table_sql)
        except BaseException:
            pass
        conn.close()

    def set_table_name(self, obj):
        self.table_name = temporary_table_name(obj, self.user)

    def _add_reverse_mapping(self, key, value):
        self.reverse_map[key] = value

    def _create_must_exist_columns(self):
        # These columns will always appear
        self.columns.append(self._create_column("context_id", alc.Integer))
        self._add_reverse_mapping("context_id", "context_id")
        self.columns.append(self._create_column("timestamp", alc.String))
        self._add_reverse_mapping("timestamp", "timestamp")
        self.columns.append(self._create_column("snapshot", alc.Boolean))
        self._add_reverse_mapping("snapshot", "snapshot")

    def _create_sql_columns(self, sql_metadata):
        # Columns from sql query
        for i, column_metadata in enumerate(sql_metadata):
            column_from_sql = self._create_column_from_sql(column_metadata)
            self.columns.append(column_from_sql)
            # to get from tuple
            # map the column's index in tuple to the column name in the dict
            self._add_reverse_mapping(i, column_metadata["name"])

    @timed
    def create_columns(self, sql_metadata, mongo_metadata):
        self.columns = []
        self._create_sql_columns(sql_metadata)
        self._create_must_exist_columns()
        self.col_map = self._create_clinical_columns(mongo_metadata)

    def _create_clinical_columns(self, mongo_metadata):
        # FH-22 ...
        # given triples of form_model, section_model and cde_models + a column name
        # create the correctly typed column in postgres
        # If the section is multiple , create ITEM_MAX columns to for each CDE in th
        # multisection   ( as opposed to "unrolling" the data )

        # e.g.:
        # if secA is non-multiple with CDEs P, Q and R
        # and secM is multiple with CDEs X and Y
        # we create columns:
        # |secA P|secA Q|secA R|secM X_1|secM Y_1|secM X_2|secM X_3|secM Y_3| ...|secM X_ITEM_MAX|secM Y_ITEM_MAX|
        # If ITEM_MAX is too small we could miss out some data ; we could calculate it but that's another query ..
        # so for now we have a constant
        column_map = mongo_metadata["multisection_column_map"]

        class ColumnOp(object):
            """
            Allows us to load column data first and then create in correct order after all column data collected
            """

            def __init__(self, rtg, columns, form_model, section_model, cde_model, column_name):
                self.rtg = rtg
                self.registry_model = rtg.registry_model
                self.columns = columns
                self.form_model = form_model
                self.section_model = section_model
                self.in_multisection = section_model.allow_multiple
                self.cde_model = cde_model
                self.column_name = column_name
                self.column_index = None
                self.has_run = False
                self.column_names = []

            @property
            def multisection_key(self):
                return (self.form_model, self.section_model)

            def run(self):
                if not self.has_run:
                    column = self._create_column()
                    if not self.in_multisection:
                        self.has_run = True
                    return column
                else:
                    return None

            def _create_column(self):
                if self.column_index is None:
                    self.rtg._create_column_from_mongo(self.column_name,
                                                       self.form_model,
                                                       self.section_model,
                                                       self.cde_model)
                    column_name = self.column_name
                else:
                    column_name = "%s_%s" % (
                        self.column_name, self.column_index)
                    self.rtg._create_column_from_mongo(column_name,
                                                       self.form_model,
                                                       self.section_model,
                                                       self.cde_model)

                return column_name

        class ColumnOps(object):

            def __init__(self, max_items):
                self.max_items = max_items
                self.column_ops = []
                self.column_names = []
                self.multisection_map = {}
                self.mongo_column_map = {}  # used to retrieve data later : maps

            def add(self, column_op):
                # rigmarole to preserve column order for the multisection items
                if column_op.in_multisection:
                    multisection_key = column_op.multisection_key
                    if multisection_key in self.multisection_map:
                        self.multisection_map[
                            multisection_key].append(column_op)
                    else:
                        self.multisection_map[multisection_key] = [column_op]
                        # first time we've hit a cde in the multisection so add the key to allow us
                        # to sequence the the items in the multisection
                        self.column_ops.append(multisection_key)
                else:
                    self.column_ops.append(column_op)

            def run(self):
                for column_op in self.column_ops:
                    if isinstance(column_op, ColumnOp):
                        column_name = column_op.run()
                        self.column_names.append(column_name)
                        self.mongo_column_map[(column_op.form_model,
                                               column_op.section_model,
                                               column_op.cde_model,
                                               None)] = column_name

                    else:
                        # multisection key
                        multisection_column_ops = self.multisection_map[
                            column_op]
                        max_items = self._get_max_items(column_op)
                        for i in range(1, max_items + 1):
                            for column_op in multisection_column_ops:
                                column_op.column_index = i
                                column_name = column_op.run()
                                self.column_names.append(column_name)
                                # when we retrieve the data from mongo this bookmarking
                                # allows the value to be slotted into the correct column
                                # in the report ...
                                self.mongo_column_map[(column_op.form_model,
                                                       column_op.section_model,
                                                       column_op.cde_model,
                                                       column_op.column_index)] = column_name

            def _get_max_items(self, multisection_key):
                # we either query or return a constant
                return self.max_items

        column_ops = ColumnOps(max_items=self.max_items)

        for ((form_model, section_model, cde_model), column_name) in list(column_map.items()):

            column_op = ColumnOp(self,
                                 self.columns,
                                 form_model,
                                 section_model,
                                 cde_model,
                                 column_name)

            column_ops.add(column_op)

        column_ops.run()

        return column_ops.mongo_column_map

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

    def _create_column_from_mongo(self, column_name, form_model, section_model, cde_model):
        column_data_type = self._get_sql_alchemy_datatype(cde_model)
        self._add_reverse_mapping(
            (form_model, section_model, cde_model), column_name)
        return self._create_column(column_name, column_data_type)

    def _get_result_messages_dict(self):
        return {"error_messages": self.error_messages,
                "warning_messages": self.warning_messages}

    @property
    def use_field_values(self):
        # field values were meant as a caching technique to speed
        # up reports
        return self.registry_model.has_feature("use_field_values")

    @timed
    def run_explorer_query(self, database_utils):
        from copy import copy
        self.create_table()
        errors = 0
        row_num = 0
        blank_row = self._get_blank_row()

        if self.use_field_values:
            generate_func = database_utils.generate_results2
        else:
            generate_func = database_utils.generate_results

        values = []
        for row in generate_func(self.reverse_map,
                                 self.col_map,
                                 max_items=self.max_items):
            new_row = copy(blank_row)
            new_row.update(row)
            values.append(new_row)
            row_num += 1

        self.engine.execute(self.table.insert(), values)

        if errors > 0:
            logger.warning("query errors: %s" % errors)
            self.error_messages.append(
                "There were %s errors running the report" % errors)

        return self._get_result_messages_dict()

    def _create_column(self, name, datatype=alc.String):
        self.column_names.append(name)
        column = alc.Column(name, datatype, nullable=True)
        self.columns.append(column)
        return column

    def create_schema(self):
        self.drop_table()
        self.table = alc.Table(self.table_name, MetaData(
            self.engine), *self.columns, schema=None)

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
        writer.writerow([self.column_labeller.get_label(key)
                         for key in list(result.keys())])
        writer.writerows(result)
        db_connection.close()
        return stream


class MongoFieldSelector(object):

    def __init__(self,
                 user,
                 registry_model,
                 query_model,
                 checkbox_ids=[],
                 longitudinal_ids=[],
                 ):
        if checkbox_ids is not None:
            self.checkbox_ids = checkbox_ids
        else:
            self.checkbox_ids = []

        self.longitudinal_ids = longitudinal_ids

        self.user = user
        self.registry_model = registry_model
        self.query_model = query_model
        self.longitudinal_map = self._get_longitudinal_cdes()
        if self.query_model:
            self.existing_data = self._get_existing_report_choices(
                self.query_model)
        else:
            self.existing_data = []

    def _get_existing_report_choices(self, query_model):
        import json
        try:
            return json.loads(query_model.projection)
        except BaseException:
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
                        self._get_field_info(
                            form_model, section_model, cde_model)

        return self.field_info

    def _get_saved_value(self, form_model, section_model, cde_model):
        if self.existing_data is None:
            return False, False

        for value_dict in self.existing_data:
            if value_dict["formName"] == form_model.name:
                if value_dict["sectionCode"] == section_model.code:
                    if value_dict["cdeCode"] == cde_model.code:
                        return value_dict["value"], value_dict.get("longitudinal", False)
        return False, False

    def _get_field_info(self, form_model, section_model, cde_model):
        saved_value, long_selected = self._get_saved_value(
            form_model, section_model, cde_model)

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
                                "savedValue": saved_value,
                                "longSelected": long_selected})

    @property
    def projections_json(self):
        # this method returns the new projection data back to the client based
        # on the list of checked items passed in ( including longitudinal if mixed report)
        # the constructed json is independent of db ids ( as these will change
        # is import of registry definition occurs
        import json
        from rdrf.models.definition.models import CommonDataElement
        from rdrf.models.definition.models import RegistryForm
        from rdrf.models.definition.models import Section
        projection_data = []

        def create_value_dict(checkbox_id):
            # <input type="checkbox" name="cb_fh_39_104_CarotidUltrasonography" id="cb_fh_39_104_CarotidUltrasonography">
            _, registry_code, form_pk, section_pk, cde_code = checkbox_id.split(
                "_")

            form_model = RegistryForm.objects.get(pk=int(form_pk))
            section_model = Section.objects.get(pk=int(section_pk))
            cde_model = CommonDataElement.objects.get(code=cde_code)

            value_dict = {}
            value_dict["registryCode"] = form_model.registry.code
            value_dict["formName"] = form_model.name
            value_dict["sectionCode"] = section_model.code
            value_dict["cdeCode"] = cde_model.code
            # we only need to store the true / checked cdes
            value_dict["value"] = True
            value_dict["longitudinal"] = self.longitudinal_map.get(
                (form_model.name, section_model.code, cde_model.code), False)
            return value_dict

        for checkbox_id in self.checkbox_ids:
            value_dict = create_value_dict(checkbox_id)
            projection_data.append(value_dict)

        return json.dumps(projection_data)

    def _get_longitudinal_cdes(self):
        from rdrf.models.definition.models import CommonDataElement
        from rdrf.models.definition.models import RegistryForm
        from rdrf.models.definition.models import Section
        d = {}
        for checkbox_id in self.longitudinal_ids:
            _, registry_code, form_pk, section_pk, cde_code, _ = checkbox_id.split(
                "_")
            form_model = RegistryForm.objects.get(pk=int(form_pk))
            section_model = Section.objects.get(pk=int(section_pk))
            cde_model = CommonDataElement.objects.get(code=cde_code)
            d[(form_model.name, section_model.code, cde_model.code)] = True
        return d


class ReportTable(object):
    """
    Used by report datatable view
    """

    def __init__(self, user, query_model):
        self.query_model = query_model
        self.user = user
        self.engine = self._create_engine()
        self.table_name = temporary_table_name(self.query_model, self.user)
        self.column_labeller = ColumnLabeller()
        self.table = self._get_table()
        self._converters = {
            "date_of_birth": str,
        }

    @property
    def title(self):
        return "Report Table"

    @property
    def columns(self):
        return [{"data": col.name, "label": self.column_labeller.get_label(
            col.name)} for col in self.table.columns]

    def _get_table(self):
        return alc.Table(
            self.table_name,
            MetaData(
                self.engine),
            autoload=True,
            autoload_with=self.engine)

    def _create_engine(self):
        return create_engine(pg_uri(settings.DATABASES["default"]))

    def run_query(self, params=None):
        from sqlalchemy.sql import select
        rows = []
        columns = [col for col in self.table.columns]
        query = select([self.table])
        if params is None:
            pass
        else:
            if "sort_field" in params:
                sort_field = params["sort_field"]
                sort_direction = params["sort_direction"]

                sort_column = getattr(self.table.c, sort_field)
                if sort_direction == "asc":
                    sort_column = sort_column.asc()
                else:
                    sort_column = sort_column.desc()

                query = query.order_by(sort_column)

        for row in self.engine.execute(query):
            result_dict = {}
            for i, col in enumerate(columns):
                result_dict[col.name] = str(self._format(col.name, row[i]))
            rows.append(result_dict)
        return rows

    def _format(self, column, data):
        if data is None:
            return ""

        if data == "{}":
            # these are artifacts of the multichoice fields
            return ""

        if isinstance(data, str):
            return data

        if isinstance(data, datetime):
            iso = data.isoformat()
            return iso

        return str(data)
