import sqlalchemy as alc
from sqlalchemy import create_engine, MetaData
from django.conf import settings
from sqlalchemy import create_engine, MetaData
from rdrf.models import ContextFormGroup


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
    PATIENT_ID = alc.Column("patient_id", alc.Integer, nullable=False)
    FORM = alc.Column("form", alc.String, nullable=False)
    FORM_GROUP = alc.Column("form_group", alc.String, nullable=False)
    SECTION = alc.Column("section", alc.String, nullable=False) 
    ITEM = alc.Column("item", alc.Integer, nullable=False)
    TIMESTAMP = alc.Column("timestamp", alc.Date, nullable=False)
    CONTEXT = alc.Column("context", alc.Integer, nullable=False)


# These columns are structural and exist on the tables
# regardless of the registry definition:

DEMOGRAPHIC_COLUMNS = [COLUMNS.PATIENT_ID]

FORM_COLUMNS = [COLUMNS.FORM_NAME,
                COLUMNS.PATIENT_ID,
                COLUMNS.TIMESTAMP]

MULTISECTION_COLUMNS = [COLUMNS.FORM_NAME,
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

TYPE_MAP = {"float": alc.Float,
            "decimal": alc.Float,
            "calculated": alc.String,
            "integer": alc.Integer,
            "Integer": alc.Integer,
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

    @property
    def datatype(self):
        return get_column_type(self.cde_model.datatype)

    @property
    def name(self):
        # this should be a nice name
        return self.cde_model.code

    @property
    def postgres(self):
        return alc.Column(self.name,
                          self.datatype,
                          nullable=True)

def get_models(registry_model):
    for form_model in registry_model.forms:
        if not form_model.is_questionnaire:
            for section_model in form_model.section_models:
                for cde_model in section_model.cde_models:
                    yield registry_model, form_model, section_model, cde_model

class SchemaGenerator(object):
    def __init__(self, registry_model):
        self.registry_model = registry_model
        self.engine = self._create_engine()
        self.has_form_groups = ContextFormGroup.objects.filter(registry=self.registry__model).count() > 0
        

    def _create_engine(self):
        # we should probably add a reporting db ...
        return create_engine(pg_uri(settings.DATABASES["reporting"]))

    def clear(self):
        # drop tables etc
        pass

    def create_tables(self):
        demographics_columns = self._get_demographic_columns()
        self._create_table("patient", demographics_columns)

        for form_model in self.registry_model.forms:
            columns = self._create_form_columns(form_model)
            self._create_table(form_model.name, columns)

            for section_model in form_model.section_models:
                if section_model.allow_multiple:
                    columns = self._create_multisection_columns(form_model,
                                                                section_model)
                    table_name = form_model.name + "_" + section_model.code
                    self._create_table(table_name, columns)


    def _create_multisection_columns(self, form_model, section_model):
        columns = [col for col in MULTISECTION_COLUMNS]
        if self.has_form_groups:
            columns.append(COLUMNS.CONTEXT)
            
            
        columns.extend([Column(self.registry_model,
                               form_model,
                               section_model,
                               cde_model).postgres
                        for cde_model in section_model.cde_models])
        return columns
            
    def _create_form_columns(self, form_model):
        columns = [col for col in FORM_COLUMNS]
        if self.has_form_groups:
            columns.append(COLUMNS.CONTEXT)
        columns.extend([Column(self.registry_model,
                       form_model,
                       section_model,
                       cde_model).postgres for section_model in form_model.section_models 
                                           for cde_model in section_model.cde_models
                                           if not section_model.allow_multiple])
        return columns

        
    def _get_demographic_columns(self):
        return []

    def _create_table(self, table_code, columns):
        table_name = table_code
        table = alc.Table(table_name, MetaData(self.engine), *columns, schema=None)
        return table
