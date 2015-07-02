from rdrf.hooking import hook

from logging import getLogger

logger = getLogger("registry_log")


@hook("patient_created_from_relative")
def mark_as_relative_in_clinical_form(patient):
    # Ensure that a patient created from a relative is marked as a relative in the clinical form
    if patient.in_registry('fh'):
        patient.set_form_value("fh", "ClinicalData", "fhDateSection", "CDEIndexOrRelative", "fh_is_relative")


@hook("registry_added")
def mark_created_patient_as_index(patient, registry_ids):
    from rdrf.models import Registry
    fh = Registry.objects.get(code="fh")
    if fh.has_feature('family_linkage') and fh.pk in registry_ids:
        logger.debug("marking patient %s as index in FH mongo db" % patient)
        patient.set_form_value("fh", "ClinicalData", "fhDateSection", "CDEIndexOrRelative", "fh_is_index")
    else:
        logger.debug("registry changed but no FH marking made for %s" % patient)
