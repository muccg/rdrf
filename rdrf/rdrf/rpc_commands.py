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


def rpc_load_matched_patient_data(request, patient_id, questionnaire_response_id):
    """
    Try to return any existing data for a patient corresponding the filled in values
    of a questionnaire filled out by on the questionnaire interface 
    NB. The curator is responsible for matching an existing patient to the incoming
    questionnaire data.
    See RDR-1229 for a description of the use case.
    
    The existing data returned is the existing questionnaire values for this matched patient ( not the data
    provided in the questionnaire response itself - which potentially may overwrite the matched data if
    the curator indicates in the approval GUI.
    """
    from registry.patients.models import Patient
    from rdrf.models import QuestionnaireResponse
    from rdrf.questionnaires import Questionnaire

    questionnaire_response_model = QuestionnaireResponse.objects.get(pk=questionnaire_response_id)
    patient_model = Patient.objects.get(pk=patient_id)
    registry_model = questionnaire_response_model.registry
    questionnaire = Questionnaire(registry_model, questionnaire_response_model)
    existing_data = questionnaire.existing_data(patient_model)

    return { "link": existing_data.link,
             "name": existing_data.name,
             "questions": existing_data.questions}


def rpc_update_selected_cdes_from_questionnaire(request, patient_id, questionnaire_response_id, questionnaire_checked_ids):
    from registry.patients.models import Patient
    from rdrf.models import QuestionnaireResponse
    from rdrf.questionnaires import Questionnaire
    from django.db import transaction
    user = request.user
    questionnaire_response_model = QuestionnaireResponse.objects.get(pk=questionnaire_response_id)
    patient_model = Patient.objects.get(pk=patient_id)
    registry_model = questionnaire_response_model.registry
    questionnaire = Questionnaire(registry_model, questionnaire_response_model)
    mongo_data_before_update = patient_model.get_dynamic_data(registry_model)

    should_revert = False

    data_to_update = [question for question in questionnaire.questions if question.src_id in questionnaire_checked_ids]
    try:
        with transaction.atomic():
            errors = questionnaire.update_patient(patient_model, data_to_update)
            if len(errors) > 0:
                raise Exception("Errors occurred during update: %s" % ",".join(errors))
    except Exception, ex:
        should_revert = True
        logger.error("Update patient failed: rolled back: %s" % ex)
        

    if not should_revert:
        questionnaire_response_model.processed = True
        questionnaire_response_model.patient_id = patient_model.pk
        questionnaire_response_model.save()
        
        return {"status": "success", "message": "Patient updated successfully"}
    else:
        logger.info("Reverting to original mongo record for patient %s" % patient_id)
        patient_model.update_dynamic_data(registry_model, mongo_data_before_update)
        
        return {"status": "fail", "message": ",".join(errors)}

def rpc_create_patient_from_questionnaire(request, questionnaire_response_id):
    from rdrf.models import QuestionnaireResponse, Registry
    from rdrf.questionnaires import PatientCreator, PatientCreatorError
    from rdrf.dynamic_data import DynamicDataWrapper
    from django.db import transaction
    
    qr = QuestionnaireResponse.objects.get(pk=questionnaire_response_id)
    patient_creator = PatientCreator(qr.registry, request.user)
    wrapper = DynamicDataWrapper(qr)
    questionnaire_data = wrapper.load_dynamic_data(qr.registry.code, "cdes")
    patient_id = None
    patient_blurb = None

    try:
        with transaction.atomic():
            created_patient = patient_creator.create_patient(None, qr, questionnaire_data)
            status = "success"
            message = "Patient created successfully"
            patient_blurb = "Patient %s created successfully" % created_patient
            patient_id = created_patient.pk

    except PatientCreatorError, pce:
        message = "Error creating patient: %s.Patient not created" % pce
        status = "fail"

    except Exception, ex:
        message = "Unhandled error during patient creation: %s. Patient not created" % ex
        status = "fail"
        
    return {"status": status,
            "message": message,
            "patient_id": patient_id,
            "patient_blurb" : patient_blurb}
