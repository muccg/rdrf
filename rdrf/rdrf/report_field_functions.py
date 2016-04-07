from rdrf.utils import report_function

@report_function
def professionals(patient_model):
    return patient_model.clinician
