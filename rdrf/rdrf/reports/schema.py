import sqlalchemy as alc
from sqlalchemy import create_engine, MetaData
from django.conf import settings
from sqlalchemy import create_engine, MetaData


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

# for registries with form groups/contexts:

# same as above but embed the context id in each form and multisection table
# as well as owning form group name




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
        return self.cde_model.code

def get_models(registry_model):
    # this won't do for form groups ...
    for form_model in registry_model.forms:
        for section_model in form_model.section_models:
               for cde_model in section_model.cde_models:
                    yield registry_model, form_model, section_model, cde_model

class SchemaGenerator(object):
    def __init__(self, registry_model):
        self.registry_model = registry_model
        self.engine = self._create_engine()

    def _create_engine(self):
        # we should probably add a reporting db ...
        return create_engine(pg_uri(settings.DATABASES["reporting"]))

    def clear(self):
        pass

    def generate(self):
        demographic_columns = self._get_demographic_columns()
        clinical_columns = [Column(registry_model,
                                   form_model,
                                   section_model,
                                   cde_model) for registry_model, form_model, section_model, cde_model in
                            get_models(self.registry_model)]

        main_columns = demographic_columns + [col for col in clinical_columns if not col.in_multisection]

        self._create_main_table(main_columns)

        multisection_columns = [col for col in clinical_columns if col._in_multisection]

        self._create_other_tables(multisection_columns)

    def _get_demographic_columns(self):
        return []

    def _create_main_table(self, columns):
        self._create_table("patient", columns)

    def _create_other_tables(self, columns):
        table_map = {}
        for col in columns:
            table_code = col.form_model.name + "_" + col.section_model.code
            if table_code in table_map:
                table_map[table_code].append(col)
            else:
                table_map[table_code] = [col]

        for table_code, cols in table_map.items():
            self._create_table(table_code,cols)

    def _create_table(self, table_code, cols):
        # create some universal columns
        columns = []
        patient_id_column = alc.Column("patient_id", alc.Integer,nullable=False)
        context_column = alc.Column("context_id", alc.Integer, nullable=False)
        last_user_column = alc.Column("user", alc.String, nullable=True)
        timestamp_column = alc.Column("timestamp", alc.Date, nullable=True)
        form_group_column = alc.Column("form_group", alc.String, nullable=True)

        columns.extend(patient_id_column,
                       context_column,
                       last_user_column,
                       timestamp_column,
                       form_group_column)

        columns.extend([self._create_column(col) for col in cols])
        
        table_name = table_code
        table = alc.Table(table_name, MetaData(self.engine), *columns, schema=None)
        return table

    def _create_column(self, col):
        return alc.Column(col.name, col.datatype, nullable=True)
