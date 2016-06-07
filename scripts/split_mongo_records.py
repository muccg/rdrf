from rdrf.models import ContextFormGroup
from rdrf.models import RDRFContext
from registry.patients.models import Patient
from django.contrib.contenttypes.models import ContentType 


class RecordSplitter(object):
    def __init__(self, registry_model):
        self.registry_model = registry_model
        self.checkup_form_group_name = "checkup"
        self.cfg = ContextFormGroup.objects.get(registry=self.registry_model,
                                                name=self.checkup_form_group_name)
        
        
        
    def run(self):
        for patient_model in Patient.objects.filter(rdrf_registry__in==[self.registry_model]):
            dynamic_data = patient_model.load_dynamic_data(self.registry_model)

            followup_form = None
            index = None

            if dynamic_data is not None:
                for i, form_dict in enumerate(dynamic_data["forms"]):
                    if form_dict["name"] == "FollowUp":
                        followup_form = form_dict
                        index = i

            if checkup_form is not None:
                form_timestamp = dynamic_data["FollowUp_timestamp"]
                del dynamic_data["forms"][index]
                del dynamic_data["FollowUp_timestamp"]
                checkup_mongo_record = self._create_additional_mongo_record(patient_model, followup_form, form_timestamp)
                
                
                

    def _create_additional_mongo_record(self, patient_model, followup_form, form_timestamp):
        content_type = ContentType.objects.get_for_model(patient_model)
        rdrf_context = RDRFContext(registry=self.registry_model, content_object=patient_model)
        rdrf_context.context_form_group = self.cfg
        rdrf_context.save()
        new_mongo_record = {"forms": [followup_form],
                            "timestamp": form_timestamp,
                            "FollowUp_timestamp": form_timestamp,
                            "django_id": patient_model.pk,
                            "django_model": "Patient",
                            "context_id": rdrf_context.pk}

        return new_mongo_record
    

        
        
        
                
                
                        
            
