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
    notifications = Notification.objects.filter(
        to_username=user.username, seen=False).order_by('-created')
    for notification in notifications:
        results.append({"message": notification.message,
                        "from_user": notification.from_username, "link": notification.link})
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
        logger.error("could not mark notification with id %s as seen: %s" %
                     (notification_id, ex))
    return status


def rpc_fh_patient_is_index(request, patient_id):
    from registry.patients.models import Patient
    patient = Patient.objects.get(pk=patient_id)
    if patient.in_registry("fh"):
        is_index = patient.get_form_value(
            "fh", "ClinicalData", "fhDateSection", "CDEIndexOrRelative") != "fh_is_relative"
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


def rpc_reporting_command(request, queryId, registry_id, command, arg):
    # 2 possible commands/invocations client side from report definition screen:
    # get_field_data: used to build all the checkboxes for client
    # get_projection: process the checked checkboxes and get json representation
    # of the selected mongo fields ( used to build temp table)
    from rdrf.reporting_table import MongoFieldSelector
    from rdrf.models import Registry
    from explorer.models import Query
    user = request.user
    if queryId == "new":
        query_model = None
    else:
        query_model = Query.objects.get(pk=int(queryId))

    registry_model = Registry.objects.get(pk=int(registry_id))
    if command == "get_projection":
        checkbox_ids = arg["checkbox_ids"]
        longitudinal_ids = arg['longitudinal_ids']
        field_selector = MongoFieldSelector(user, registry_model, query_model, checkbox_ids, longitudinal_ids)
        result = field_selector.projections_json
        logger.debug("projections_json = %s" % result)
        return result
    elif command == "get_field_data":
        field_selector = MongoFieldSelector(user, registry_model, query_model)
        return field_selector.field_data
    else:
        raise Exception("unknown command: %s" % command)


# RDRF Context Switching
def rpc_rdrf_context_command(request, registry_code, patient_id, context_command):
    from rdrf_contexts import RDRFContextCommandHandler, RDRFContextError
    try:
        handler = RDRFContextCommandHandler(request, registry_code, patient_id)
        result = handler.run(context_command)
        return {"status": "success", "command_result": result}
    except RDRFContextError, err:
        logger.error("Error changing context for patient id %s registry code %s command %s: %s" % (patient_id,
                                                                                                   registry_code,
                                                                                                   context_command,
                                                                                                   err))
        return {"status": "failure", "error": err.message}


def rpc_get_patient_contexts(request, registry_code, patient_id):
    logger.debug("rpc get_patient_contexts: %s %s" % (registry_code, patient_id))
    from rdrf.models import Registry
    from registry.patients.models import Patient
    from rdrf.dynamic_data import DynamicDataWrapper
    try:
        patient_model = Patient.objects.get(pk=patient_id)
    except Patient.DoesNotExist:
        return {"status": "failure", "error": "Patient does not exist"}

    try:
        registry_model = Registry.objects.get(code=registry_code)
    except Registry.DoesNotExist:
        return {"status": "failure", "error": "Registry does not exist"}

    wrapper = DynamicDataWrapper(patient_model)


    def created_date(context_model):
        return context_model.created_at.strftime("%A, %d. %B %Y %I:%M%p")

    logger.debug("loading saved contexts for patient %s" % patient_id)
    context_models = wrapper.load_contexts(registry_model)

    context_data = [{"name": context_model.display_name,
                     "id": context_model.pk,
                     "createdAt": created_date(context_model)} for context_model in context_models]
    logger.debug("context data = %s" % context_data)

    return {"status": "success", "data": context_data}


def rpc_registry_supports_contexts(request, registry_code):
    from rdrf.models import Registry
    try:
        registry_model = Registry.objects.get(code=registry_code)
        return registry_model.has_feature("contexts")
    except Registry.DoesNotExist:
        return False


# questionnaire handling


def rpc_load_patient_data(request, patient_id, questionnaire_response_id):
    """
    Retrieve any data already entered for the questions in questionnaire
    """
    from rdrf.models import QuestionnaireResponse
    from registry.patients.models import Patient
    from rdrf.utils import iterate_record
    from explorer.views import Humaniser
    from rdrf.models import RegistryForm, Section, CommonDataElement
    
    questionnaire_response_model = QuestionnaireResponse.objects.get(questionnaire_response_id)
    
    patient_model = Patient.objects.get(pk=patient_id)
    
    patient_data = patient_model.get_dynamic_data(questionnnaire_response_model.registry)

    questionaire_data = questionnaire_response_model.data

    humaniser = Humaniser(questionnaire_response_model.registry)

    cdes_to_check = OrderedSet([])

    for form_dict, section_dict, index, cde_dict in iterate_record(questionnaire_data):
        cdes_to_check.add((form_dict["name"], section_dict["code"], cde_dict["code"]))

    patient_values = []

    for form_dict, section_dict, index, cde_dict in iterate_record(patient_data):
        triple = (form_dict["name"], section_dict["code"], cde_dict["code"])
        if triple in cdes_to_check:
            form_model = RegistryForm.objects.get(registry=registry_model,
                                                  name=form_dict["name"])
            section_model = Section.objects.get(code=section_dict["code"])
            cde_model = CommonDataElement.objects.get(code=cde_dict["code"])
            display_value = humaniser.display_value2(form_model,
                                                     section_model,
                                                     cde_model,
                                                     cde_dict["value")

                    
            item = {"name": cde_dict["name"


    return patient_values
            
        
    

    
    



    
    
    
        
    
