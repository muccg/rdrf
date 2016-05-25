from rdrf.hooking import hook
from rdrf.models import RDRFContext, ContextFormGroup
from rdrf.models import Registry
from rdrf.dynamic_data import DynamicDataWrapper
from django.contrib.contenttypes.models import ContentType

from logging import getLogger
logger = getLogger("registry_log")


def get_default_context(fh_registry_model, patient_model):
    # clinical form is member of default form group 
    cfg = fh_registry_model.default_context_form_group
    content_type = ContentType.objects.get_for_model(patient_model)
    # can't use usual get_or_create as generic
    try:
        default_context = RDRFContext.objects.get(registry=fh_registry_model,
                                                  context_form_group=cfg,
                                                  object_id=patient_model.pk)
    except RDRFContext.DoesNotExist:
        default_context = RDRFContext(registry=fh_registry_model,
                                      context_form_group=cfg,
                                      content_object=patient_model)
    
        default_context.display_name = cfg.get_default_name(patient_model)
        default_context.save()

    logger.debug("default context = %s" % default_context)
    return default_context


def get_main_context(fh_registry_model, patient_model):
    """
    Return the context where we need to stick the index/relative field value
    I.e. the context which has that non-multiple (static) form group containing 
    the main clinical form
    """
    for context_model in patient_model.context_models:
        if context_model.context_form_group
        and context_model.context_form-group.pk == fh_registry_model.default_context_form_group.pk:
            return context_model


@hook("patient_created_from_relative")
def mark_as_relative_in_clinical_form(patient):
    # Ensure that a patient created from a relative is marked as a relative in the clinical form
    logger.debug("marking patient %s as relative .." % patient.pk)
    if patient.in_registry('fh'):
        fh = Registry.objects.get(code="fh")
        default_context = get_main_context(fh, patient)
        
        patient.set_form_value("fh",
                               "ClinicalData",
                               "fhDateSection",
                               "CDEIndexOrRelative",
                               "fh_is_relative",
                               context_model=default_context)
        logger.debug("marked patient as relative ok")


@hook("registry_added")
def mark_created_patient_as_index(patient, registry_ids):

    def has_no_mongo_data(patient, registry_model):
        logger.debug("checking mongo data")
        context_model  = get_main_context(registry_model, patient)
        if context_model is None:
            logger.debug("context model is None")
            # true when a new patient
            return True
        wrapper = DynamicDataWrapper(patient, rdrf_context_id=context_model.pk)
        data = wrapper.load_dynamic_data(registry_model.code, 'cdes')
        logger.debug("loaded dynamic data = %s" % data)
        if data is None:
            logger.debug("mongo data None")
            return True
        else:
            logger.debug("mongo record exists")
            return False

    fh = Registry.objects.get(code="fh")

    if fh.has_feature('family_linkage') and fh.pk in registry_ids and has_no_mongo_data(patient, fh):
        logger.debug("marking patient %s as index .." % patient.pk)

        # patient has just been added to fh
        # get the current context form group
        try:
            logger.debug("fh registry added hook running setting to index")
            default_context = get_main_context(fh, patient)
            patient.set_form_value("fh",
                                   "ClinicalData",
                                   "fhDateSection",
                                   "CDEIndexOrRelative",
                                   "fh_is_index",
                                   context_model=default_context)
            logger.debug("marked patient as index ok")

        except Exception, ex:
            logger.error("error running hook: %s" % ex)
            
