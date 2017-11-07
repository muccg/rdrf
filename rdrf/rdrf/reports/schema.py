import sqlalchemy as alc
from sqlalchemy import create_engine, MetaData
from django.conf import settings
from rdrf.models import ContextFormGroup
from registry.patients.models import Patient
import logging
from psycopg2 import ProgrammingError
from psycopg2 import IntegrityError
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType

logger = logging.getLogger(__name__)

# generate relational schema
# but what schema?
# most "natural" seems to be this:
# for registries without form groups, context_id is redundant and confusing
# so better to not extract at all - hence:
# one demographics table
# one table per form
# multisections of forms have to be separate tables
# one table for addresses
# one table for consents
# one table for relatives
# one history table (?)
# if there are questionnaires:
# questionnaire responses ?
# for registries with form groups ( Just FH at the moment)
# same as above but embed the context id in each form and multisection table
# as well as owning form group name


# Column representations which are reused
class COLUMNS:
    PATIENT_ID = ("patient_id", alc.Integer, False)
    FORM = ("form", alc.String, False)
    FORM_GROUP = ("form_group", alc.String, False)
    SECTION = ("section", alc.String, False)
    ITEM = ("item", alc.Integer, False)
    TIMESTAMP = ("timestamp", alc.Date, True)
    CONTEXT = ("context", alc.Integer, False)




# These columns are structural and exist on the tables
# regardless of the registry definition:
DEMOGRAPHIC_COLUMNS = [COLUMNS.PATIENT_ID]

FORM_COLUMNS = [COLUMNS.FORM,
                COLUMNS.PATIENT_ID,
                COLUMNS.TIMESTAMP]

MULTISECTION_COLUMNS = [COLUMNS.FORM,
                        COLUMNS.SECTION,
                        COLUMNS.ITEM,
                        COLUMNS.TIMESTAMP,
                        COLUMNS.PATIENT_ID]

class TableType:
    DEMOGRAPHIC = 1
    CLINICAL_FORM = 2
    MULTISECTION = 3


class DataSource(object):
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
        if self.section_model:
            self.is_multiple = section_model.allow_multiple
        else:
            self.is_multiple = False
        self.cde_model = cde_model
        self.field = field

    @property
    def datatype(self):
        return self.cde_model.datatype.lower().strip()


    @property
    def column_name(self):
        return self.column.name

    def get_value(self, patient_model, context_model=None):
       if context_model is None:
           context_model = patient_model.default_context(self.registry_model)
           
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
            return context_id
        elif self.field == "section":
            return self.section_model.display_name
        elif self.field == "timestamp":
            return patient_model.get_form_timestamp(self.form_model, context_model)
            
        else:
            raise Exception("Unknown field: %s" % self.field)

    def _get_cde_value(self, patient_model, context_model):
        try:
            raw_value = patient_model.get_form_value(self.registry_model.code,
                                                 self.form_model.name,
                                                 self.section_model.code,
                                                 self.cde_model.code,
                                                 False,
                                                 context_id=context_model.pk)


        except KeyError:
            # the dynamic data record is empty
            return None
        
        value = self.cde_model.get_display_value(raw_value)
        return self._fix_datatype(value)

    def _fix_datatype(self, value):
        if self.datatype != "string":
            if value == "":
                # this is a bug in the display value?
                return None
        return value

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
    datatype = cde_model.datatype.lower().strip()
    return TYPE_MAP.get(datatype, alc.String)


class Column(object):
    def __init__(self, registry_model, form_model, section_model, cde_model, column_map):
        self.registry_model = registry_model
        self.form_model = form_model
        self.section_model = section_model
        self.cde_model = cde_model
        self.in_multisection = section_model.allow_multiple
        self.column_map = column_map # ref to global map

    @property
    def datatype(self):
        return get_column_type(self.cde_model)

    @property
    def name(self):
        # this should be a nice name
        return self.cde_model.code

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

class ClinicalTable(object):
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

class MultiSectionExtractor(object):
    def __init__(self, registry_model, clinical_table, datasources):
        self.registry_model = registry_model
        self.clinical_table = clinical_table
        self.datasources = datasources

    def get_rows(self, patient_model, context_model=None):
        
        if context_model is None:
            context_model = patient_model.default_context(self.registry_model)

        items_list = patient_model.evaluate_field_expression(self.registry_model,
                                                             self.field_expression)

        return self._convert_to_rows(patient_model, context_model, items_list)

    def _convert_to_rows(self, patient_model, context_model, items_list):
        for index, item_dict in enumerate(items_list):
            item_number = index + 1
            row_dict = {}
            row_dict["form"] = self.clinical_table.form_model.name
            row_dict["section"] = self.clinical_table.section_model.display_name
            row_dict["item"] = item_number
            row_dict["patient_id"] = patient_model.pk
            for cde_code in item_dict:
                raw_value = item_dict[cde_code]
                reporting_value = self._get_reporting_value(cde_code, raw_value)
                row_dict[cde_code] = reporting_value
            yield row_dict

    @property
    def field_expression(self):
        return "$ms/%s/%s/items" % (self.clinical_table.form_model.name,
                                    self.clinical_table.section_model.code)
    def _get_reporting_value(self, cde_code, raw_value):
        return raw_value
    
        

class Generator(object):
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
        logger.debug("copying data for table %s" % table.name)
        dest_engine.execute("DROP TABLE IF EXISTS %s CASCADE" % table.name)
        table.create(dest_engine)
        rows = src_engine.execute(table.select()).fetchall()

        with dest_engine.begin() as con:
            for row in rows:
                con.execute(table.insert().values(**row))

    def _get_sql_alchemy_type(self, db_type):
        return alc.String

    def clear(self):
        # drop tables etc
        for table in self.table_list:
            self._drop_table(table)

    def _create_demographic_tables(self):
        from registry.patients.models import Patient
        from registry.patients.models import PatientAddress, AddressType, State, NextOfKinRelationship
        from rdrf.models import ConsentQuestion, ConsentSection, Registry, RegistryForm
        from rdrf.models import Section, CommonDataElement, CDEPermittedValueGroup, CDEPermittedValue
        from explorer.models import Query

    
        

        starting_models = [ContentType,Registry, Group, State, AddressType, NextOfKinRelationship,
                           PatientAddress, Query, Section, ConsentSection, ConsentQuestion,
                           RegistryForm, CDEPermittedValue,
                           CDEPermittedValueGroup, CommonDataElement,Patient]


        

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
                logger.debug("Adding %s" % model.__name__)
                models.append(model)
                

        for model in starting_models:
            add_model(model)

        logger.debug("demographic models = %s" % [m.__name__ for m in models])

        def clone_model(model):
            table_name = model._meta.db_table
            self._mirror_table(
                table_name, self.default_engine, self.reporting_engine)
            logger.debug("mirrored table %s OK" % table_name)


        def add_models(models):
            bad = []
            for model in models:
                if model is not None:
                    try:
                        clone_model(model)
                    except:
                        bad.append(model)
            return bad

        finished = False
        n = 1
        while not finished and n < 100:
            models = add_models(models)
            finished = len(models) == 0
            n += 1

        if not finished:
            raise Exception("Could not dump all demographic models: %s" % [m.__name__ for m in models])

        logger.info("Dumped all demographic data OK")


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
        except:
            pass

        source_meta = MetaData(bind=source_engine)
        table = alc.Table(table_name, source_meta, autoload=True)
        table.metadata.create_all(self.reporting_engine)
        self._copy_table_data(source_engine, target_engine, table)

    def create_tables(self):
        if self.reporting_engine is not self.default_engine:
            logger.info("CREATING DEMOGRAPHIC TABLES")
            self._create_demographic_tables()

        logger.info("CREATING CLINICAL TABLES")

        for form_model in self.registry_model.forms:
            logger.debug("creating table for clinical form %s" %
                         form_model.name)
            columns = self._create_form_columns(form_model)
            table = self._create_table(form_model.name, columns)

            single_form_table = ClinicalTable(TableType.CLINICAL_FORM,
                                              table,
                                              columns,
                                              form_model)
            

            self.clinical_tables.append(single_form_table) 
            
            for section_model in form_model.section_models:
                if section_model.allow_multiple:
                    logger.info("creating multisection table for %s %s" % (form_model.name,
                                                                           section_model.code))

                    columns = self._create_multisection_columns(form_model,
                                                                section_model)
                    table_name = form_model.name + "_" + section_model.code
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
        from registry.patients.models import Patient
        logger.info("EXTRACTING CLINICAL DATA")
        logger.debug("column map = %s" % self.column_map)
        form_tables = [t for t in self.clinical_tables if not t.is_multisection]
        multi_tables = [t for t in self.clinical_tables if t.is_multisection]
        for clinical_table in form_tables:
            logger.debug("processing form table %s" % clinical_table)
            datasources = [self.column_map[column] for column in clinical_table.columns]
            if not self.has_form_groups:
            
                for patient_model in self.patients:
                    row = {ds.column_name: ds.get_value(patient_model) for ds in datasources}
                    self.reporting_engine.execute(clinical_table.table.insert().values(**row))
                    logger.debug("inserted row: %s" % row)
            else:
                raise NotImplementedError("registry has form groups")

        for clinical_table in multi_tables:
            logger.info("processing table for multisection %s" % clinical_table)
            datasources = [self.column_map[column] for column in clinical_table.columns]
            multisection_extractor = MultiSectionExtractor(self.registry_model, clinical_table, datasources)
            if not self.has_form_groups:
               for patient_model in self.patients:
                   for item_row in multisection_extractor.get_rows(patient_model):
                       self.reporting_engine.execute(clinical_table.table.insert().values(**item_row))
            else:
                raise NotImplementedError("registry has form groups")
                
                       
            
            
            

    def _create_multisection_columns(self, form_model, section_model):
        columns = [self.mkcol(col, form_model=form_model, field=col[0]) for col in MULTISECTION_COLUMNS]
        if self.has_form_groups:
            columns.append(self.mkcol(COLUMNS.CONTEXT,
                                      form_model=form_model,
                                      section_model=section_model))

        columns.extend([Column(self.registry_model,
                               form_model,
                               section_model,
                               cde_model,
                               self.column_map).postgres
                        for cde_model in section_model.cde_models])
        return columns

    def _create_form_columns(self, form_model):
        columns = [self.mkcol(col, form_model=form_model, field=col[0])
                   for col in FORM_COLUMNS]
        if self.has_form_groups:
            columns.append(self.mkcol(COLUMNS.CONTEXT,
                                      form_model=form_model,
                                      field="context_id"))

        columns.extend([Column(self.registry_model,
                               form_model,
                               section_model,
                               cde_model,
                               self.column_map).postgres for section_model in form_model.section_models
                        for cde_model in section_model.cde_models
                        if not section_model.allow_multiple])
        return columns

    def _get_table_name(self, name):
        return name.replace(" ", "").lower()

    def _create_table(self, table_code, columns):
        table_name = self._get_table_name("rep_" + table_code)
        logger.debug("creating table %s" % table_name)
        self._drop_table(table_name)
        table = alc.Table(table_name, MetaData(
            self.reporting_engine), *columns, schema=None)
        table.create()
        # these cause failures in migration ...
        logger.debug("created table %s OK" % table_name)
        return table

    def _drop_table(self, table_name):
        drop_table_sql = "DROP TABLE IF EXISTS %s CASCADE" % table_name
        conn = self.reporting_engine.connect()
        try:
            conn.execute(drop_table_sql)
            logger.debug("dropped existing table %s" % table_name)
        except Exception as ex:
            logger.debug("could not drop table %s: %s" % (table_name,
                                                          ex))

        conn.close()
