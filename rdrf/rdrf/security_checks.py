from registry.patients.models import ParentGuardian

def check_patient_user(user, patient_model):
    if user.is_patient or user.is_parent or user.is_carrier:
        # check self patient
        if user.self_patient:
            if user.self_patient.pk == patient_model.pk:
                return True

        # check parent guardian and own children
        for parent in ParentGuardian.objects.filter(user=user):
            if patient_model in parent.children:
                return True

        return False
    else:
        return True
    

    

    
    

    

        
        
