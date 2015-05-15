import logging
logger = logging.getLogger('registry_log')


def rpc_visibility(request, element):
    user = request.user
    if user.can("see", element):
        return True


def rpc_check_notifications(request):
    from rdrf.models import Notification
    user = request.user
    results = []
    notifications = Notification.objects.filter(to_username=user.username, seen=False).order_by('-created')
    for notification in notifications:
        results.append({"message": notification.message, "from_user": notification.from_username, "link": notification.link})
    return results


def rpc_dismiss_notification(request, notification_id):
    from rdrf.models import Notification
    status = False
    try:
        notification = Notification.objects.get(pk=int(notification_id))
        notification.seen = True
        notification.save()
        status = True
    except Exception as ex:
        logger.error("could not mark notification with id %s as seen: %s" % (notification_id, ex))
    return status


def rpc_fh_patient_is_index(request, patient_id):
    from registry.patients.models import Patient
    patient = Patient.objects.get(pk=patient_id)
    if patient.in_registry("fh"):
            is_index = patient.get_form_value("fh", "ClinicalData", "fhDateSection", "CDEIndexOrRelative") != "fh_is_relative"
            return is_index
    else:
        return False


# Molecular Data Validation
def rpc_validate_dna(request, field_value):
    from rdrf.genetic_validation import GeneticValidator, GeneticType
    validator = GeneticValidator()
    return validator.validate(field_value, GeneticType.DNA)


def rpc_validate_exon(request, field_value):
    from rdrf.genetic_validation import GeneticValidator, GeneticType
    validator = GeneticValidator()
    return validator.validate(field_value, GeneticType.EXON)


def rpc_validate_rna(request, field_value):
    from rdrf.genetic_validation import GeneticValidator, GeneticType
    validator = GeneticValidator()
    return validator.validate(field_value, GeneticType.RNA)


def rpc_validate_protein(request, field_value):
    from rdrf.genetic_validation import GeneticValidator, GeneticType
    validator = GeneticValidator()
    return validator.validate(field_value, GeneticType.PROTEIN)