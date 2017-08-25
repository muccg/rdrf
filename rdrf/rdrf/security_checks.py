from registry.patiets.models import Patient
from registry.patients.models import ParentGuardian

def check_patient_user(user, patient_model):
    if user.is_patient or user.is_parent or user.is_carrier:

        # check patients who have registred as users with this user
        for user_patient in Patient.objects.filter(user=user):
            if user_patient.pk == patient_model.pk:
                return True
        
        # check parent guardian self patient and own children
        for parent in ParentGuardian.objects.filter(user=user):
            if patient_model in parent.children:
                return True
            if parent.self_patient and parent.self_patient.pk == patient_model.pk:
                return True

        return False
    else:
        return True
