import logging
logger = logging.getLogger('registry_log')


def rpc_create_fh_patient_from_relative(relative_pk, family_name, given_names):
    from registry.patients.models import Patient
    from registry.patients.models import PatientRelative
    relative = PatientRelative.objects.get(pk=relative_pk)
    logger.info("creating a patient for relative %s" % relative)
    p = Patient()
    p.family_name = family_name
    p.given_names = given_names
    p.date_of_birth = '1965-06-14' #todo remove hardcoded dob for patientrelative
    p.consent = True
    p.active = True
    p.save()
    relative.relative_patient = p
    relative.save()

    return p.pk
