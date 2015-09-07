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
    from rdrf.dynamic_data import DynamicDataWrapper

    def has_no_mongo_data(patient):
        wrapper = DynamicDataWrapper(patient)
        data = wrapper.load_dynamic_data('fh', 'cdes')
        return data is None

    fh = Registry.objects.get(code="fh")

    if fh.has_feature('family_linkage') and fh.pk in registry_ids and has_no_mongo_data(patient):
        # patient has just been added to fh
        logger.debug("fh registry added hook running setting to index")
        patient.set_form_value("fh", "ClinicalData", "fhDateSection", "CDEIndexOrRelative", "fh_is_index")
