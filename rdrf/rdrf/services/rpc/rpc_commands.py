import logging

logger = logging.getLogger(__name__)


def rpc_visibility(request, element):
    user = request.user
    if user.can("see", element):
        return True


def rpc_reset_session_timeout(request):
    from datetime import datetime

    dt = datetime.now()
    request.session["_session_security"] = dt.strftime("%Y-%m-%dT%H:%M:%S.%f")
    return {}


def rpc_check_notifications(request):
    from rdrf.models.definition.models import Notification

    user = request.user
    results = []
    notifications = Notification.objects.filter(
        to_username=user.username, seen=False
    ).order_by("-created")
    for notification in notifications:
        results.append(
            {
                "message": notification.message,
                "from_user": notification.from_username,
                "link": notification.link,
            }
        )
    return results


def rpc_dismiss_notification(request, notification_id):
    from rdrf.models.definition.models import Notification

    status = False
    try:
        notification = Notification.objects.get(pk=int(notification_id))
        notification.seen = True
        notification.save()
        status = True
    except Exception as ex:
        logger.error(
            "could not mark notification with id %s as seen: %s" % (notification_id, ex)
        )
    return status


def rpc_fh_patient_is_index(request, patient_id):
    from registry.patients.models import Patient

    patient = Patient.objects.get(pk=patient_id)
    if patient.in_registry("fh"):
        is_index = (
            patient.get_form_value(
                "fh", "ClinicalData", "fhDateSection", "CDEIndexOrRelative"
            )
            != "fh_is_relative"
        )
        return is_index
    else:
        return False


# Molecular Data Validation
def rpc_validate_dna(request, field_value):
    from rdrf.forms.validation.genetic_validation import GeneticValidator, GeneticType

    validator = GeneticValidator()
    return validator.validate(field_value, GeneticType.DNA)


def rpc_validate_exon(request, field_value):
    from rdrf.forms.validation.genetic_validation import GeneticValidator, GeneticType

    validator = GeneticValidator()
    return validator.validate(field_value, GeneticType.EXON)


def rpc_validate_rna(request, field_value):
    from rdrf.forms.validation.genetic_validation import GeneticValidator, GeneticType

    validator = GeneticValidator()
    return validator.validate(field_value, GeneticType.RNA)


def rpc_validate_protein(request, field_value):
    from rdrf.forms.validation.genetic_validation import GeneticValidator, GeneticType

    validator = GeneticValidator()
    return validator.validate(field_value, GeneticType.PROTEIN)


def rpc_reporting_command(request, query_id, registry_id, command, arg):
    # 2 possible commands/invocations client side from report definition screen:
    # get_field_data: used to build all the checkboxes for client
    # get_projection: process the checked checkboxes and get json representation
    # of the selected mongo fields ( used to build temp table)
    from rdrf.services.io.reporting.reporting_table import MongoFieldSelector
    from rdrf.models.definition.models import Registry
    from explorer.models import Query

    user = request.user
    if query_id == "new":
        query_model = None
    else:
        query_model = Query.objects.get(pk=int(query_id))

    registry_model = Registry.objects.get(pk=int(registry_id))
    if command == "get_projection":
        checkbox_ids = arg["checkbox_ids"]
        longitudinal_ids = arg["longitudinal_ids"]
        field_selector = MongoFieldSelector(
            user, registry_model, query_model, checkbox_ids, longitudinal_ids
        )
        result = field_selector.projections_json
        return result
    elif command == "get_field_data":
        field_selector = MongoFieldSelector(user, registry_model, query_model)
        return field_selector.field_data
    else:
        raise Exception("unknown command: %s" % command)


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
    from rdrf.models.definition.models import QuestionnaireResponse
    from rdrf.workflows.questionnaires.questionnaires import Questionnaire

    questionnaire_response_model = QuestionnaireResponse.objects.get(
        pk=questionnaire_response_id
    )
    patient_model = Patient.objects.get(pk=patient_id)
    registry_model = questionnaire_response_model.registry
    questionnaire = Questionnaire(registry_model, questionnaire_response_model)
    existing_data = questionnaire.existing_data(patient_model)

    return {
        "link": existing_data.link,
        "name": existing_data.name,
        "questions": existing_data.questions,
    }


def rpc_update_selected_cdes_from_questionnaire(
    request, patient_id, questionnaire_response_id, questionnaire_checked_ids
):
    from registry.patients.models import Patient
    from rdrf.models.definition.models import QuestionnaireResponse
    from rdrf.workflows.questionnaires.questionnaires import Questionnaire
    from django.db import transaction

    questionnaire_response_model = QuestionnaireResponse.objects.get(
        pk=questionnaire_response_id
    )
    patient_model = Patient.objects.get(pk=patient_id)
    registry_model = questionnaire_response_model.registry
    questionnaire = Questionnaire(registry_model, questionnaire_response_model)
    data_to_update = [
        question
        for question in questionnaire.questions
        if question.src_id in questionnaire_checked_ids
    ]

    try:
        with transaction.atomic():
            errors = questionnaire.update_patient(patient_model, data_to_update)
            if len(errors) > 0:
                raise Exception("Errors occurred during update: %s" % ",".join(errors))
    except Exception as ex:
        logger.error("Update patient failed: rolled back: %s" % ex)
        return {"status": "fail", "message": ",".join(errors)}
    else:
        questionnaire_response_model.processed = True
        questionnaire_response_model.patient_id = patient_model.pk
        questionnaire_response_model.save()
        return {"status": "success", "message": "Patient updated successfully"}


def rpc_create_patient_from_questionnaire(request, questionnaire_response_id):
    from rdrf.models.definition.models import QuestionnaireResponse
    from rdrf.workflows.questionnaires.questionnaires import (
        PatientCreator,
        PatientCreatorError,
    )
    from rdrf.db.dynamic_data import DynamicDataWrapper
    from django.db import transaction
    from django.urls import reverse

    qr = QuestionnaireResponse.objects.get(pk=questionnaire_response_id)
    patient_creator = PatientCreator(qr.registry, request.user)
    wrapper = DynamicDataWrapper(qr)
    questionnaire_data = wrapper.load_dynamic_data(qr.registry.code, "cdes")
    patient_id = None
    patient_blurb = None
    patient_link = None
    created_patient = "Not Created!"

    try:
        with transaction.atomic():
            created_patient = patient_creator.create_patient(
                None, qr, questionnaire_data
            )
            status = "success"
            message = "Patient created successfully"
            patient_blurb = "Patient %s created successfully" % created_patient
            patient_id = created_patient.pk
            patient_link = reverse("patient_edit", args=[qr.registry.code, patient_id])

    except PatientCreatorError as pce:
        message = "Error creating patient: %s.Patient not created" % pce
        status = "fail"

    except Exception as ex:
        message = (
            "Unhandled error during patient creation: %s. Patient not created" % ex
        )
        status = "fail"

    return {
        "status": status,
        "message": message,
        "patient_id": patient_id,
        "patient_name": "%s" % created_patient,
        "patient_link": patient_link,
        "patient_blurb": patient_blurb,
    }


def rpc_get_timeout_config(request):
    from django.conf import settings
    from rdrf.helpers.utils import get_site_url

    timeout = settings.SESSION_SECURITY_EXPIRE_AFTER
    warning = settings.SESSION_SECURITY_WARNING
    # login url looks like https://<SITE_URL>/<SITE_NAME>/account/login?next=/<SITE_NAME>/router/

    site_url = get_site_url(request)
    site_name = settings.SITE_NAME  # this should only be set on prod really
    if "localhost" not in site_url:
        if site_url.endswith("/"):
            login_url = (
                site_url + site_name + "/account/login?next=/" + site_name + "/router/"
            )
        else:
            login_url = (
                site_url
                + "/"
                + site_name
                + "/account/login?next=/"
                + site_name
                + "/router/"
            )
    else:
        # localhost in dev has no site_name
        # http://localhost:8000/account/login?next=/router/
        if site_url.endswith("/"):
            login_url = site_url + "account/login?next=/router/"
        else:
            login_url = site_url + "/" + "account/login?next=/router/"

    return {"timeout": timeout, "warning": warning, "loginUrl": login_url}


def rpc_get_forms_list(request, registry_code, patient_id, form_group_id):
    from rdrf.models.definition.models import ContextFormGroup
    from rdrf.models.definition.models import Registry
    from registry.patients.models import Patient
    from rdrf.security.security_checks import security_check_user_patient
    from django.core.exceptions import PermissionDenied
    from rdrf.forms.components import FormsButton
    from django.utils.translation import ugettext as _

    user = request.user
    fail_response = {"status": "fail", "message": _("Data could not be retrieved")}

    try:
        registry_model = Registry.objects.get(code=registry_code)
    except Registry.DoesNotExist:
        return fail_response

    try:
        patient_model = Patient.objects.get(id=patient_id)
    except Patient.DoesNotExist:
        return fail_response

    try:
        security_check_user_patient(user, patient_model)
    except PermissionDenied:
        return fail_response

    if not patient_model.in_registry(registry_model.code):
        return fail_response

    if not user.is_superuser and not user.in_registry(registry_model):
        return fail_response

    if form_group_id is not None:
        try:
            context_form_group = ContextFormGroup.objects.get(id=form_group_id)
        except ContextFormGroup.DoesNotExist:
            logger.warning(
                f"ContextFormGroup does not exist for form_group_id: {form_group_id}"
            )
            return fail_response
    else:
        context_form_group = None

    forms = context_form_group.forms if context_form_group else registry_model.forms

    form_models = [
        f for f in forms if f.applicable_to(patient_model) and user.can_view(f)
    ]

    html = FormsButton(
        registry_model, user, patient_model, context_form_group, form_models
    ).html

    return {"status": "success", "html": html}


def rpc_check_verification(
    request,
    registry_code,
    patient_id,
    context_id,
    form_name,
    section_code,
    item_index,
    cde_code,
    value,
):
    from rdrf.models.definition.verification_models import check_verification

    is_verified = check_verification(
        registry_code,
        patient_id,
        context_id,
        form_name,
        section_code,
        item_index,
        cde_code,
        value,
    )

    return {"status": "success", "verified": is_verified}
