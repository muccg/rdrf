import logging
logger = logging.getLogger('registry_log')


def rpc_fh_create_patient(minimal_data):
    logger.debug("creating patient with data %s" % minimal_data)
    from registry.patients.models import Patient
    p = Patient()
    p.family_name = minimal_data['family_name']
    p.given_names = minimal_data['given_names']
    p.active = True
    pk = p.save()
    return pk
