class VerifiableCDE:
    def __init__(self, registry_model, cde_dict):
        self.registry_model = registry_model
        self.valid = False
        self._load(cde_dict)

    def _load(self, cde_dict):
        form_name = cde_dict.get("form", None)
        section_code = cde_dict.get("section", None)
        cde_code = cde_dict.get("cde", None)
        for form_model in registry_model.form_models:
            if form_model.name == form_name:
                for section_model in form_model.section_models:
                    if section_model.code == section_code:
                        if not section_model.allow_multiple:
                            for cde_models in section_model.cde_models:
                                if cde_model.code == cde_code:
                                    self.form_model = form_model
                                    self.section_model = section_model
                                    self.cde_model = cde_model
                                    self.allow_multiple = False
                                    self.valid = True


    def get_data(self):
        if not self.valid:
            return None
                                         
        
    

def get_verifiable_cdes(registry_model):
    
    if registry_model.has_feature("verification"):
        return filter(lambda v : v.valid == True,
                      [VerifiableCDE(registry_model, cde_dict) for cde_dict in metadata.get("verification_cdes", [])])
    
    return []
   

            
        
        
