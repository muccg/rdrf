import sqlalchemy as alc
from sqlalchemy import create_engine, MetaData
from django.conf import settings
from rdrf.models.definition.models import ContextFormGroup
from rdrf.models.definition.models import CommonDataElement
from rdrf.models.definition.models import ClinicalData
from rdrf.db.dynamic_data import DynamicDataWrapper
from rdrf.forms.progress.form_progress import FormProgress
from rdrf.helpers.utils import cached
from registry.patients.models import Patient
import logging
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
import re
from functools import lru_cache
from operator import attrgetter

logger = logging.getLogger(__name__)

MAX_TABLE_NAME_LENGTH = 63


def unambigious_name(section_code, cde_code):
    return no_space_lower(section_code + "_" + cde_code)


def lower_strip(s):
    return s.lower().strip()


def no_space_lower(s):
    return s.replace(" ", "").lower()


class COLUMNS:
    PATIENT_ID = ("patient_id", alc.Integer, False)
    FORM = ("form", alc.String, False)
    FORM_GROUP = ("form_group", alc.String, True)
    SECTION = ("section", alc.String, False)
    ITEM = ("item", alc.Integer, False)
    TIMESTAMP = ("timestamp", alc.DateTime, True)
    CONTEXT = ("context_id", alc.Integer, False)
    PROGRESS = ("progress", alc.Integer, True)
    USER = ("username", alc.String, True)  # last user to edit
    # snapshot id  - null means CURRENT
    SNAPSHOT = ("snapshot", alc.Integer, True)


# If CDEs are labelled poorly it is possible to generate name clashes within the same table
# we use a global name map to avoid this

nice_name_map = {}

# These columns are structural and exist on the tables
# regardless of the registry definition:
DEMOGRAPHIC_COLUMNS = [COLUMNS.PATIENT_ID]

FORM_COLUMNS = [COLUMNS.FORM,
                COLUMNS.CONTEXT,
                COLUMNS.FORM_GROUP,
                COLUMNS.PATIENT_ID,
                COLUMNS.USER,
                COLUMNS.PROGRESS,
                COLUMNS.TIMESTAMP]

MULTISECTION_COLUMNS = [COLUMNS.FORM,
                        COLUMNS.CONTEXT,
                        COLUMNS.SECTION,
                        COLUMNS.ITEM,
                        COLUMNS.FORM_GROUP,
                        COLUMNS.USER,
                        COLUMNS.TIMESTAMP,
                        COLUMNS.PATIENT_ID]


class TableType:
    DEMOGRAPHIC = 1
    CLINICAL_FORM = 2
    MULTISECTION = 3


def fix_display_value(datatype, value):
    if value == "" and datatype != "string":
        return None
    else:
        return value


def in_context(context_model, clinical_table):
    # contexts only contain all form data if there are NO form groups explicitly assigned
    if not context_model.context_form_group:
        return True
    else:
        return clinical_table.form_model in context_model.context_form_group.forms


def get_form_group(context_model):
    if not context_model.context_form_group:
        return None
    else:
        return context_model.context_form_group.direct_name


@cached
def get_cde_model(code):
    return CommonDataElement.objects.get(code=code)


@cached
def nice_name(s):
    """
    Make the column names in postgres easy to work with and match the names
    that appear on the screen so that report writers don't have to look
    up cde codes.
    """
    label = lower_strip(s)
    nice = re.sub(r'[^a-z0-9]', "_", label)
    nice = re.sub("_+", "_", nice)
    if nice.endswith("_"):
        nice = nice[:-1]
    return nice


@lru_cache(maxsize=100)
def get_clinical_data(registry_code, patient_id, context_id):
    patient_model = Patient.objects.get(pk=patient_id)
    wrapper = DynamicDataWrapper(patient_model, rdrf_context_id=context_id)
    return wrapper.load_dynamic_data(registry_code, "cdes")


@lru_cache(maxsize=100)
def get_nested_clinical_data(registry_code, patient_id, context_id):
    patient_model = Patient.objects.get(pk=patient_id)
    wrapper = DynamicDataWrapper(patient_model, rdrf_context_id=context_id)
    return wrapper.load_dynamic_data(registry_code, "cdes", flattened=False)


class DataSource:
    def __init__(self,
                 registry_model,
                 column,
                 form_model=None,
                 section_model=None,
                 cde_model=None,
                 field=None):
        self.registry_model = registry_model
        self.column = column
        self.form_model = form_model
        self.section_model = section_model
        self.form_progress = FormProgress(self.registry_model)
        self.progress_percentage = None
        if self.section_model:
            self.is_multiple = section_model.allow_multiple
        else:
            self.is_multiple = False
        self.cde_model = cde_model
        self.field = field

    @property
    def datatype(self):
        return lower_strip(self.cde_model.datatype)

    @property
    def column_name(self):
        return self.column.name

    def get_value(self, patient_model, context_model):
        if self.field:
            return self._get_field_value(patient_model, context_model)
        else:
            return self._get_cde_value(patient_model, context_model)

    def _get_field_value(self, patient_model, context_model):
        if self.field == "patient_id":
            return patient_model.pk
        elif self.field == "form":
            return self.form_model.name
        elif self.field == "context_id":
            return context_model.pk
        elif self.field == "section":
            return self.section_model.display_name
        elif self.field == "form_group":
            return get_form_group(context_model)
        elif self.field == "username":
            return self._get_last_user(patient_model, context_model)
        elif self.field == "timestamp":
            return patient_model.get_form_timestamp(self.form_model, context_model)
        elif self.field == "progress":
            return self._get_form_progress(patient_model, context_model)
        else:
            raise Exception("Unknown field: %s" % self.field)

    def _get_form_progress(self, patient_model, context_model):
        if self.progress_percentage is None:
            self.progress_percentage = self.form_progress.get_form_progress(self.form_model,
                                                                            patient_model,
                                                                            context_model)
        return self.progress_percentage

    def _get_last_user(self, patient_model, context_model):
        # last user to edit the _form_ in this context
        history = ClinicalData.objects.collection(
            self.registry_model.code, "history")
        snapshots = history.find(patient_model, record_type="snapshot")
        snapshots = sorted([s for s in snapshots],
                           key=attrgetter("pk"), reverse=True)
        for snapshot in snapshots:
            if snapshot.data and "record" in snapshot.data:
                record = snapshot.data["record"]
                if "context_id" in record:
                    if context_model.pk == record["context_id"]:
                        if "form_name" in snapshot.data:
                            form_name = snapshot.data["form_name"]
                            if form_name == self.form_model.name:
                                if "form_user" in snapshot.data:
                                    return snapshot.data["form_user"]

    def _get_cde_value(self, patient_model, context_model):
        try:
            data = get_clinical_data(self.registry_model.code,
                                     patient_model.pk,
                                     context_model.pk)

            raw_value = patient_model.get_form_value(self.registry_model.code,
                                                     self.form_model.name,
                                                     self.section_model.code,
                                                     self.cde_model.code,
                                                     False,
                                                     context_id=context_model.pk,
                                                     clinical_data=data)

        except KeyError:
            # the dynamic data record is empty
            return None

        value = self.cde_model.get_display_value(raw_value)
        return fix_display_value(self.cde_model.datatype, value)


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


TYPE_MAP = {"float": alc.Float,
            "decimal": alc.Float,
            "calculated": alc.String,
            "integer": alc.Integer,
            "int": alc.Integer,
            "string": alc.String,
            "date": alc.Date,
            "range": alc.String,
            "file": alc.String}


def get_column_type(cde_model):
    datatype = lower_strip(cde_model.datatype)
    return TYPE_MAP.get(datatype, alc.String)


class Column:
    def __init__(self, registry_model, form_model, section_model, cde_model, column_map, code_map=None):
        self.registry_model = registry_model
        self.form_model = form_model
        self.section_model = section_model
        self.cde_model = cde_model
        self.in_multisection = section_model.allow_multiple
        self.column_map = column_map  # ref to global map
        self.column_name_prefix = None

        if code_map is not None:
            code_count = code_map.get(self.cde_model.code, 0)
            if code_count > 0:
                # cde model resused on form
                self.column_name_prefix = self.section_model.code
                code_map[self.cde_model.code] += 1
            else:
                code_map[self.cde_model.code] = 1

    @property
    def datatype(self):
        return get_column_type(self.cde_model)

    @property
    def name(self):
        # return no_space_lower(self.section_model.code + "_" + self.cde_model.code)
        return unambigious_name(self.section_model.code, self.cde_model.code)

    @property
    def postgres(self):
        column = alc.Column(self.name,
                            self.datatype,
                            nullable=True)

        datasource = DataSource(self.registry_model,
                                column=column,
                                form_model=self.form_model,
                                section_model=self.section_model,
                                cde_model=self.cde_model)

        self.column_map[column] = datasource
        return column


class ClinicalTable:
    def __init__(self, table_type,
                 table,
                 columns,
                 form_model,
                 section_model=None):
        self.table_type = table_type
        self.table = table
        self.columns = columns
        self.form_model = form_model
        self.section_model = section_model

    @property
    def is_multisection(self):
        return self.section_model and self.section_model.allow_multiple

    def __str__(self):
        return self.table.name


class MultiSectionExtractor:
    def __init__(self, registry_model, clinical_table, datasources):
        self.registry_model = registry_model
        self.clinical_table = clinical_table
        self.datasources = datasources

    def get_rows(self, patient_model, context_model):

        nested_clinical_data = get_nested_clinical_data(self.registry_model.code,
                                                        patient_model.pk,
                                                        context_model.pk)

        items_list = patient_model.evaluate_field_expression(self.registry_model,
                                                             self.field_expression,
                                                             clinical_data=nested_clinical_data)

        return self._convert_to_rows(patient_model, context_model, items_list)

    def _convert_to_rows(self, patient_model, context_model, items_list):
        form_timestamp = patient_model.get_form_timestamp(
            self.clinical_table.form_model, context_model=context_model)

        for index, item_dict in enumerate(items_list):
            item_number = index + 1
            row_dict = {}
            row_dict["form"] = self.clinical_table.form_model.name
            row_dict["section"] = self.clinical_table.section_model.display_name
            row_dict["item"] = item_number
            row_dict["patient_id"] = patient_model.pk
            row_dict["context_id"] = context_model.pk
            row_dict["timestamp"] = form_timestamp

            for cde_code in item_dict:
                cde_model = CommonDataElement.objects.get(code=cde_code)
                is_file = lower_strip(cde_model.datatype) == "file"
                # column_name = no_space_lower(cde_code)
                column_name = unambigious_name(self.clinical_table.section_model.code, cde_code)
                raw_value = item_dict[cde_code]
                reporting_value = self._get_reporting_value(
                    cde_code, raw_value, is_file=is_file)
                row_dict[column_name] = reporting_value
            yield row_dict

    @property
    def field_expression(self):
        return "$ms/%s/%s/items" % (self.clinical_table.form_model.name,
                                    self.clinical_table.section_model.code)

    def _get_reporting_value(self, cde_code, raw_value, is_file=False):
        cde_model = get_cde_model(cde_code)
        display_value = cde_model.get_display_value(raw_value)
        if is_file:
            try:
                filename = display_value.get("file_name", "NO_FILE")
                file_id = display_value.get("django_file_id", "NO_FILE_ID")
                display_value = "%s/%s" % (filename, file_id)
            except Exception as ex:
                logger.warning("Error getting file details: %s" % ex)
                display_value = None

        return fix_display_value(cde_model.datatype.lower().strip(), display_value)


class Generator:
    def __init__(self, registry_model, db="reporting"):
        self.registry_model = registry_model
        self.clinical_engine = self._create_engine("clinical")
        self.default_engine = self._create_engine("default")
        self.has_form_groups = ContextFormGroup.objects.filter(
            registry=registry_model).count() > 0
        self.table_list = []
        self.clinical_tables = []
        self.column_map = {}

        if db == "clinical":
            self.reporting_engine = self.clinical_engine
        elif db == "default":
            self.reporting_engine = self.default_engine
        elif db == "reporting":
            self.reporting_engine = self._create_engine("reporting")
        else:
            raise Exception(
                "Unknown db: %s. Should be one of clinical | default" % db)

    def mkcol(self, triple, form_model=None, section_model=None, cde_model=None, field=None):
        column_name = triple[0]
        column_datatype = triple[1]
        is_nullable = triple[2]
        column = alc.Column(column_name, column_datatype, nullable=is_nullable)
        datasource = DataSource(self.registry_model,
                                column,
                                form_model=form_model,
                                section_model=section_model,
                                cde_model=cde_model,
                                field=field)

        self.column_map[column] = datasource
        return column

    def _create_engine(self, db_name="default"):
        # we should probably add a reporting db ...
        return create_engine(pg_uri(settings.DATABASES[db_name]))

    def _get_table_for_model(self, model, db_name="default"):

        if db_name == "default":
            engine = self.default_engine
        else:
            engine = self.engine

        table = alc.Table(model._meta.db_table,
                          MetaData(engine), autoload=True)
        return table

    def _copy_table_data(self, src_engine, dest_engine, table):
        dest_engine.execute("DROP TABLE IF EXISTS %s CASCADE" % table.name)
        table.create(dest_engine)
        rows = src_engine.execute(table.select()).fetchall()

        with dest_engine.begin() as con:
            for row in rows:
                con.execute(table.insert().values(**row))

    def clear(self):
        # drop tables etc
        for table in self.table_list:
            self._drop_table(table)

    def _create_demographic_tables(self):
        from registry.patients.models import PatientAddress, AddressType, State, NextOfKinRelationship
        from registry.patients.models import ConsentValue
        from rdrf.models.definition.models import ConsentQuestion, ConsentSection, Registry, RegistryForm
        from rdrf.models.definition.models import Section, CommonDataElement, CDEPermittedValueGroup, CDEPermittedValue
        from explorer.models import Query

        starting_models = [
            ContentType,
            Registry,
            Group,
            State,
            AddressType,
            NextOfKinRelationship,
            PatientAddress,
            Query,
            Section,
            ConsentSection,
            ConsentQuestion,
            ConsentValue,
            RegistryForm,
            CDEPermittedValue,
            CDEPermittedValueGroup,
            CommonDataElement,
            Patient]

        if self.reporting_engine is self.default_engine:
            raise Exception("reporting db = default!")

        models = []

        def exists(model):
            return model.__name__ in [m.__name__ for m in models]

        def add_model(model):
            for m in self._get_related_models(model):
                if m.__name__ == model.__name__:
                    continue
                add_model(m)
            if not exists(model):
                models.append(model)

        for model in starting_models:
            add_model(model)

        def clone_model(model):
            table_name = model._meta.db_table
            self._mirror_table(
                table_name, self.default_engine, self.reporting_engine)

        def add_models(models):
            bad = []
            for model in models:
                if model is not None:
                    try:
                        clone_model(model)
                    except BaseException:
                        bad.append(model)
            return bad

        finished = False
        n = 1
        while not finished and n < 100:
            models = add_models(models)
            finished = len(models) == 0
            n += 1

        if not finished:
            raise Exception("Could not dump all demographic models: %s" % [
                            m.__name__ for m in models])

    def _get_related_models(self, model):
        models = [model]
        for field in model._meta.related_objects:
            related_model = field.related_model
            if related_model not in models:
                models.append(related_model)
            models.extend(self._get_related_models(related_model))

        return models

    def _mirror_table(self, table_name, source_engine, target_engine):
        try:
            self._drop_table(table_name)
        except BaseException:
            pass

        source_meta = MetaData(bind=source_engine)
        table = alc.Table(table_name, source_meta, autoload=True)
        table.metadata.create_all(self.reporting_engine)
        self._copy_table_data(source_engine, target_engine, table)

    def create_tables(self):
        if self.reporting_engine is not self.default_engine:
            self._create_demographic_tables()

        for form_model in self.registry_model.forms:
            if form_model.name.startswith("GeneratedQuestionnaire"):
                continue

            columns = self._create_form_columns(form_model)
            table = self._create_table(form_model.name, columns)

            single_form_table = ClinicalTable(TableType.CLINICAL_FORM,
                                              table,
                                              columns,
                                              form_model)

            self.clinical_tables.append(single_form_table)

            for section_model in form_model.section_models:
                if section_model.allow_multiple:

                    columns = self._create_multisection_columns(form_model,
                                                                section_model)
                    table_name = form_model.name + "_" + section_model.code

                    if len(table_name) > MAX_TABLE_NAME_LENGTH:
                        table_name = table_name[:MAX_TABLE_NAME_LENGTH]

                    if "!" in table_name:
                        table_name = table_name.replace("!", "")

                    table = self._create_table(table_name, columns)
                    multisection_table = ClinicalTable(TableType.MULTISECTION,
                                                       table,
                                                       columns,
                                                       form_model,
                                                       section_model)

                    self.clinical_tables.append(multisection_table)

        self._extract_clinical_data()

    @property
    def patients(self):
        return Patient.objects.filter(rdrf_registry__in=[self.registry_model])

    def _extract_clinical_data(self):
        form_tables = [
            t for t in self.clinical_tables if not t.is_multisection]
        multi_tables = [t for t in self.clinical_tables if t.is_multisection]
        for clinical_table in form_tables:
            row_count = 0
            datasources = [self.column_map[column]
                           for column in clinical_table.columns]
            for patient_model in self.patients:
                for context_model in patient_model.context_models:
                    if context_model.registry.id == self.registry_model.id:
                        if in_context(context_model, clinical_table):
                            row = {ds.column_name: ds.get_value(
                                patient_model, context_model) for ds in datasources}
                            self.reporting_engine.execute(
                                clinical_table.table.insert().values(**row))
                            row_count += 1

        for clinical_table in multi_tables:
            row_count = 0
            current_column_names = set(
                [col.name for col in clinical_table.table.columns])
            datasources = [self.column_map[column]
                           for column in clinical_table.columns]
            multisection_extractor = MultiSectionExtractor(
                self.registry_model, clinical_table, datasources)
            for patient_model in self.patients:
                for context_model in patient_model.context_models:
                    if context_model.registry.id == self.registry_model.id:
                        if in_context(context_model, clinical_table):
                            for item_row in multisection_extractor.get_rows(
                                    patient_model, context_model):
                                self._clean_row(item_row, current_column_names)
                                self.reporting_engine.execute(
                                    clinical_table.table.insert().values(**item_row))
                                row_count += 1

    def _clean_row(self, row, current_column_names):
        bad_keys = set(row.keys()) - current_column_names
        if bad_keys:
            logger.warning("BAD COLUMNS IN DATA: %s" % bad_keys)
        for k in bad_keys:
            row.pop(k, None)

    def _create_multisection_columns(self, form_model, section_model):
        columns = [self.mkcol(col, form_model=form_model, field=col[0])
                   for col in MULTISECTION_COLUMNS]

        columns.extend([Column(self.registry_model,
                               form_model,
                               section_model,
                               cde_model,
                               self.column_map).postgres
                        for cde_model in section_model.cde_models])
        return columns

    def _create_form_columns(self, form_model):

        code_map = {}

        columns = [self.mkcol(col, form_model=form_model, field=col[0])
                   for col in FORM_COLUMNS]

        columns.extend([Column(self.registry_model,
                               form_model,
                               section_model,
                               cde_model,
                               self.column_map,
                               code_map).postgres for section_model in form_model.section_models
                        for cde_model in section_model.cde_models
                        if not section_model.allow_multiple])
        return columns

    def _get_table_name(self, name):
        return no_space_lower(name)

    def _create_table(self, table_code, columns):
        table_name = self._get_table_name(table_code)
        if "!" in table_name:
            table_name = table_name.replace("!", "")

        self._drop_table(table_name)
        table = alc.Table(table_name, MetaData(
            self.reporting_engine), *columns, schema=None)
        table.create()
        # these cause failures in migration ...
        return table

    def _drop_table(self, table_name):
        drop_table_sql = "DROP TABLE IF EXISTS %s CASCADE" % table_name
        conn = self.reporting_engine.connect()
        try:
            conn.execute(drop_table_sql)
        except Exception as ex:
            logger.warning("could not drop table %s: %s" % (table_name,
                                                            ex))

        conn.close()
