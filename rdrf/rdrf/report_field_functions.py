from rdrf.utils import report_function
from registry.patients.models import PatientAddress


@report_function
def professionals(patient_model):
    return patient_model.clinician

@report_function
def country(patient_model):
    try:
        patient_address = PatientAddress.objects.get(patient=patient_model)
        return patient_address.country
    except:
        pass
    

