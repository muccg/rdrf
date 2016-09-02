from rdrf.models import Registry

class DataImporter(object):
    def __init__(self, registry_code, import_file):
        self.registry_code = registry_code
        self.registry_model = Registry.objects.get(code=self.registry_code)
        self.import_file = import_file
        self.created_patient_ids = []
        
    def run(self):
        try:
            with transaction.atomic():
                self._run()
        except Exception, ex:
            self.rollback_mongo()

    def _run(self):
        for row in self._get_rows():
            patient_model = self._create_patient_model(row)
            patient_model.save()

            for form_model in self.registry_model.forms:
                
                form_data = self._get_form_data(form_model, row)
                try:
                    self.submit_form_data(patient_model, form_model, form_data)
                except FormError, fex:
                    print "Error submitting form"


    def _get_form_data(self, form_model, row):
        for section_model in form_model.section_models:
            if not section_model.allow_multiple:
                for cde_model in section_model.cde_models:
                    


    def _get_form_key_and_data(self, form_model, section_model, cde_model, row):
        field_num = self._get_field_num(form_model, section_model, cde_model)
        field_value = self._get_field_value(row, field_num)
        if cde_model.pv_group:
            # range
            field_value = self._get_pvg_code(cde_model, form_value)
        field_key  = self._get_field_key(form_model, section_model, cde_model)
        return field_key, field_value
    
        
                    
                        
            
        
        
        
                    
                    
                    
                
                
                
                
