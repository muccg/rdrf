from registry.patients.models import Patient
from registry.patients.models import ParentGuardian
from django.core.exceptions import PermissionDenied
import logging

logger = logging.getLogger(__name__)

def _get_prop(user, prop):
    # case where site does not have prop defined
    try:
        return getattr(user, prop)
    except:
        return False

def _user_is_patient_type(user):
    return any([_get_prop(user, "is_patient"),
                _get_prop(user, "is_parent"),
                _get_prop(user, "is_carrier")])


def _security_violation(user, patient_model):
    logger.info("SECURITY VIOLATION User %s Patient %s" % (user.pk,
                                                           patient_model.pk))
    raise PermissionDenied()

def security_check_user_patient(user, patient_model):
    # either user is allowed to act on this record ( return True)
    # or not ( raise PermissionDenied error)
    if user.is_superuser:
        return True

    if _user_is_patient_type(user):
        # check patients who have registered as users with this user
        for user_patient in Patient.objects.filter(user=user):
            if user_patient.pk == patient_model.pk:
                # user IS patient
                return True
        
        # check parent guardian self patient and own children
        for parent in ParentGuardian.objects.filter(user=user):
            if patient_model in parent.children:
                return True
            if parent.self_patient and parent.self_patient.pk == patient_model.pk:
                return True

        _security_violation(user, patient_model)

    
    # user is staff of some sort
    patient_wg_ids = set([wg.id for wg in patient_model.working_groups.all()])
    user_wg_ids = set([wg.id for wg in user.working_groups.all()])

    overlap = patient_wg_ids & user_wg_ids
    
    if overlap:
        return True

    _security_violation(user, patient_model)
