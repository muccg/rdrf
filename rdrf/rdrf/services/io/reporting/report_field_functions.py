from rdrf.helpers.utils import report_function
from registry.patients.models import PatientAddress


@report_function
def professionals(patient_model):
    return patient_model.clinician


@report_function
def country(patient_model):
    try:
        patient_address = PatientAddress.objects.get(patient=patient_model)
        return patient_address.country
    except BaseException:
        pass


@report_function
def last_login(patient_model):
    # if there is a user associated with this patient
    # return it's last login time
    # this only makes sense for FKRP like registries
    user = patient_model.user
    if user is not None:
        return user.last_login
