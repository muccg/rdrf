import sqlalchemy as alc
from sqlalchemy import create_engine, MetaData
from django.conf import settings
from rdrf.models import ContextFormGroup
import logging
from copy import deepcopy
from django.db import connections
import inspect

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
    TIMESTAMP = ("timestamp", alc.Date, False)
    CONTEXT = ("context", alc.Integer, False)


def mkcol(triple):
    return alc.Column(triple[0],triple[1],nullable=triple[2])

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



# Maps RDRF CDE datatypes to postgres column type

TYPE_MAP = {"float": alc.Float,
            "decimal": alc.Float,
            "calculated": alc.String,
            "integer": alc.Integer,
            "int": alc.Integer,
            "string": alc.String,
            "date": alc.Date,
            "range": alc.String,
            "file": alc.String,
}


def get_column_type(cde_model):
    datatype = cde_model.datatype.lower().strip()
    return TYPE_MAP.get(datatype, alc.String)


class Column(object):
    def __init__(self, registry_model, form_model, section_model, cde_model):
        self.registry_model = registry_model
        self.form_model = form_model
        self.section_model = section_model
        self.cde_model = cde_model
        self.in_multisection = section_model.allow_multiple
        logger.debug(type(self.cde_model))
        

    @property
    def datatype(self):
        return get_column_type(self.cde_model)

    @property
    def name(self):
        # this should be a nice name
        return self.cde_model.code

    @property
    def postgres(self):
        logger.debug("COLUMN: %s %s nullable=%s" % (self.name,
                                                    self.datatype,
                                                    True))
        return alc.Column(self.name,
                          self.datatype,
                          nullable=True)

def get_models(registry_model):
    for form_model in registry_model.forms:
        if not form_model.is_questionnaire:
            for section_model in form_model.section_models:
                for cde_model in section_model.cde_models:
                    yield registry_model, form_model, section_model, cde_model

class Generator(object):
    def __init__(self, registry_model, db="reporting"):
        self.registry_model = registry_model
        self.clinical_engine = self._create_engine("clinical")
        self.default_engine = self._create_engine("default")
        self.has_form_groups = ContextFormGroup.objects.filter(registry=registry_model).count() > 0
        self.alc_tables = []
        self.table_list = []

        # perhaps better to make this the default 
        #self.reporting_engine = self._create_engine("reporting")
        if db == "clinical":
            self.reporting_engine = self.clinical_engine
        elif db == "default":
            self.reporting_engine = self.default_engine
        elif db == "reporting":
            self.reporting_engine = self._create_engine("reporting")
        else:
            raise Exception("Unknown db: %s. Should be one of clinical | default" % db)
        

    def _create_engine(self, db_name="default"):
        # we should probably add a reporting db ...
        return create_engine(pg_uri(settings.DATABASES[db_name]))


    def _get_table_for_model(self, model, db_name="default"):

        if db_name == "default":
            engine = self.default_engine
        else:
            engine = self.engine
            
        table = alc.Table(model._meta.db_table, MetaData(engine), autoload=True)
        return table

    def _copy_table_data(self, src_engine, dest_engine, table):
        logger.debug("copying data for table %s" % table.name)
        dest_engine.execute("DROP TABLE IF EXISTS %s CASCADE" % table.name)
        table.create(dest_engine)
        self.alc_tables.append(table)
        rows = src_engine.execute(table.select()).fetchall()


        with dest_engine.begin() as con:
            for row in rows:
                logger.debug("insert row %s" % row)
                con.execute(table.insert().values(**row))

    def _get_sql_alchemy_type(self, db_type):
        return alc.String
        

    def clear(self):
        # drop tables etc
        for table in self.table_list:
            self._drop_table(table)

    def _create_demographic_tables(self):
        from registry.patients.models import Patient
        from registry.patients.models import PatientAddress, AddressType, State
        from rdrf.models import ConsentQuestion, ConsentSection, Registry, RegistryForm
        from rdrf.models import Section, CommonDataElement, CDEPermittedValueGroup, CDEPermittedValue
        

        starting_models = [State, AddressType, PatientAddress, Registry, Section, RegistryForm, CDEPermittedValue, CDEPermittedValueGroup, CommonDataElement,Patient]
        if self.reporting_engine is self.default_engine:
            raise Exception("reporting db = default!")

        models = []

        def exists(model):
            return model.__name__ in [m.__name__ for m in models]
        

        for model in starting_models:
            if not exists(model):
                models.append(model)
                
            related_models = self._get_related_models(model)
            for related_model in related_models:
                if not exists(related_model):
                    models.append(related_model)

        models.reverse()
        logger.debug("demographic models = %s" % [m.__name__ for m in models])

        for model in models:
            if model is not None:
                table_name = model._meta.db_table
                logger.debug("mirroring table %s" % table_name)
                self._mirror_table(table_name, self.default_engine, self.reporting_engine)


    def _get_django_models_from_module(self, module):
        from django.db.models import Model

        def _retrieve_objects_from_module(module, predicate_func):
            things = []
            for thing_name, thing in inspect.getmembers(module):
                try:
                    if predicate_func(thing):
                        things.append(thing)
                except:
                    pass
            return things
                        

        def is_django_system_model(thing):
            return issubclass(thing, Model) and thing.__name__.startswith("django.")

        def is_rdrf_model(thing):
            return issubclass(thing, Model) and thing.__name__.startswith("django.")

        models =  [ thing for thing_name, thing in inspect.getmembers(module) if is_rdrf_model(thing)]
        logger.debug("models for module %s = %s" % (module.__name__,
                                                    models))
        return models


    def _get_related_models(self, model):
        logger.debug("getting related model of %s" % model.__name__)
        models = [model]
        for field in model._meta.related_objects:
            related_model = field.related_model
            if not related_model in models:
                models.append(related_model)
                logger.debug("added related model %s" % related_model.__name__)
            models.extend(self._get_related_models(related_model))
                
        return models

    def _mirror_table(self, table_name, source_engine, target_engine):
        try:
            self._drop_table(table_name)
        except:
            pass

        source_meta = MetaData(bind=source_engine)
        table = alc.Table(table_name, source_meta, autoload=True)
        #table.metadata.create_all(self.reporting_engine)
        self._copy_table_data(source_engine, target_engine, table)
        

    def create_tables(self):
        if self.reporting_engine is not self.default_engine:
            logger.debug("creating demographic tables ...")
            self._create_demographic_tables()

        for form_model in self.registry_model.forms:
            logger.debug("creating table for clinical form %s" % form_model.name)
            columns = self._create_form_columns(form_model)
            self._create_table(form_model.name, columns)

            for section_model in form_model.section_models:
                if section_model.allow_multiple:
                    columns = self._create_multisection_columns(form_model,
                                                                section_model)
                    table_name = form_model.name + "_" + section_model.code
                    logger.debug("creating table for multisection %s" % table_name)
                    self._create_table(table_name, columns)


    def _create_multisection_columns(self, form_model, section_model):
        columns = [mkcol(col) for col in MULTISECTION_COLUMNS]
        if self.has_form_groups:
            columns.append(mkcol(COLUMNS.CONTEXT))
            
            
        columns.extend([Column(self.registry_model,
                               form_model,
                               section_model,
                               cde_model).postgres
                        for cde_model in section_model.cde_models])
        return columns
            
    def _create_form_columns(self, form_model):
        columns = [mkcol(col) for col in FORM_COLUMNS]
        if self.has_form_groups:
            columns.append(mkcol(COLUMNS.CONTEXT))
            
        columns.extend([Column(self.registry_model,
                       form_model,
                       section_model,
                       cde_model).postgres for section_model in form_model.section_models 
                                           for cde_model in section_model.cde_models
                                           if not section_model.allow_multiple])
        return columns

        
    def _get_demographic_columns(self):
        return []

    def _get_table_name(self, name):
        return name.replace(" ","").lower()

    def _create_table(self, table_code, columns):
        logger.debug("creating table %s" % table_name)
        table_name = self._get_table_name("rep_" + table_code)
        self._drop_table(table_name)
        table = alc.Table(table_name, MetaData(self.reporting_engine), *columns, schema=None)
        table.create()
        # these cause failures in migration ...
        self.alc_tables.append(table)
        return table

    def _drop_table(self, table_name):
        drop_table_sql = "DROP TABLE %s CASCADE" % table_name
        conn = self.reporting_engine.connect()
        try:
            conn.execute(drop_table_sql)
        except Exception as ex:
            logger.debug("could not drop table %s: %s" % (table_name,
                                                          ex))
            
        conn.close()

