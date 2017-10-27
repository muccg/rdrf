# generate relational schema from registry definition

class Column(object):
    def __init__(self, registry_model, form_model, section_model, cde_model):
        self.registry_model = registry_model
        self.form_model = form_model
        self.section_model = section_model
        self.cde_model = cde_model
        self.in_multisection = section_model.allow_multiple

    @property
    def datatype(self):
        pass

def get_models(registry_model):
    for form_model in registry_model.forms:
        for section_model in form_model.section_models:
               for cde_model in section_model.cde_models:
                    yield registry_model, form_model, section_model, cde_model

class SchemaGenerator(object):
    def __init__(self, registry_model, reporting_db_conn):
        self.registry_model = registry_model
        self.conn = reporting_db_conn

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
        pass

    def _create_other_tables(self, columns):
        pass

        

        

    
        
