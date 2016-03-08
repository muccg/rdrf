from rdrf.hooking import hook
from rdrf.models import RDRFContext, ContextFormGroup
from rdrf.models import Registry
from rdrf.dynamic_data import DynamicDataWrapper

from logging import getLogger
logger = getLogger("registry_log")

@hook("patient_created_from_relative")
def mark_as_relative_in_clinical_form(patient):
    # Ensure that a patient created from a relative is marked as a relative in the clinical form
    if patient.in_registry('fh'):
        fh = Registry.objects.get(code="fh")
        cfg = fh.default_context_form_group
        new_context = RDRFContext(registry=fh,
                                  context_form_group=cfg,
                                  content_object=patient)
        new_context.display_name = cfg.get_default_name(patient)
        new_context.save()
        
        patient.set_form_value("fh",
                               "ClinicalData",
                               "fhDateSection",
                               "CDEIndexOrRelative",
                               "fh_is_relative",
                               context_model=new_context)


@hook("registry_added")
def mark_created_patient_as_index(patient, registry_ids):

    def get_clinical_context(patient_model, registry_model):
        for context_model in patient_model.context_models:
           if context_model.context_form_group.pk == registry_model.default_context_form_group.pk:
               return context_model

    def has_no_mongo_data(patient, registry_model):
        logger.debug("checking mongo data")
        context_model  = get_clinical_context(patient, registry_model)
        if context_model is None:
            # true when a new patient
            return True
        wrapper = DynamicDataWrapper(patient, rdrf_context_id=context_model.pk)
        data = wrapper.load_dynamic_data(registry_model.code, 'cdes')
        logger.debug("loaded dynamic data = %s" % data)
        return data is None

    fh = Registry.objects.get(code="fh")

    if fh.has_feature('family_linkage') and fh.pk in registry_ids and has_no_mongo_data(patient, fh):
        # patient has just been added to fh
        # get the current context form group
        try:
            cfg = fh.default_context_form_group
            new_context = RDRFContext(registry=fh,
                                      context_form_group=cfg,
                                      content_object=patient)

            new_context.display_name = cfg.get_default_name(patient)
            
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
            
