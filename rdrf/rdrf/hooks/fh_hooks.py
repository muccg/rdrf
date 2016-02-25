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

    def has_no_mongo_data(patient, registry_model):
        logger.debug("checking mongo data")
        default_context = patient.default_context(registry_model)
        if default_context is None:
            # for new patient this will be true
            return True
        wrapper = DynamicDataWrapper(patient, rdrf_context_id=default_context.pk)
        data = wrapper.load_dynamic_data(registry_model.code, 'cdes')
        logger.debug("loaded dynamic data = %s" % data)
        return data is None

    fh = Registry.objects.get(code="fh")

    if fh.has_feature('family_linkage') and fh.pk in registry_ids and has_no_mongo_data(patient, fh):
        # patient has just been added to fh
        # get the current context form group
        from rdrf.models import RDRFContext, ContextFormGroup
        try:
            cfg = ContextFormGroup.objects.filter(registry=fh, name="Default").get()
            new_context = RDRFContext(registry=fh,
                                      context_form_group=cfg,
                                      content_object=patient)

            new_context.display_name = cfg.get_default_name()
            
            new_context.save()
            logger.debug("fh registry added hook running setting to index")
            patient.set_form_value("fh",
                                   "ClinicalData",
                                   "fhDateSection",
                                   "CDEIndexOrRelative",
                                   "fh_is_index",
                                   context_model=new_context)

        except Exception, ex:
            logger.error("error running hook: %s" % ex)
            
