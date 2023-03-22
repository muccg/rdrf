from rdrf.celery import app
from intframework.utils import get_event_code
from intframework.updater import HL7Handler
import hl7
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

logger.info("registering tasks ...")


@app.task(name="rdrf.services.tasks.run_custom_action")
def run_custom_action(custom_action_id, user_id, patient_id, input_data):
    from rdrf.models.definition.models import CustomAction
    from registry.groups.models import CustomUser
    from registry.patients.models import Patient

    if patient_id != 0:
        patient_model = Patient.objects.get(id=patient_id)
    else:
        patient_model = None

    user = CustomUser.objects.get(id=user_id)
    try:
        custom_action = CustomAction.objects.get(id=custom_action_id)
    except CustomAction.DoesNotExist:
        logger.error(f"can't run custom action {custom_action_id} as it doesn't exist")
        return

    return custom_action.execute(user, patient_model, input_data)


@app.task(name="rdrf.services.tasks.handle_hl7_message")
def handle_hl7_message(umrn, message: hl7.Message):
    logger.info(f"processing task for umrn {umrn}")
    try:
        event_code = get_event_code(message)
    except Exception as ex:
        logger.error(f"error getting event code for message: {ex}")
        event_code = "unknown"
    logger.info(f"HL7 handler: {umrn} {event_code} received")
    hl7_handler = HL7Handler(umrn=umrn, hl7message=message, username="updater")
    response_data = hl7_handler.handle()
    if response_data:
        logger.info(f"HL7 handler: {umrn} {event_code} processed")
    else:
        logger.error(f"HL7 handler: {umrn} {event_code} failed")
    return response_data


@app.task(name="rdrf.services.tasks.recalculate_cde")
def recalculate_cde(
    patient_id,
    registry_code,
    context_id,
    form_name,
    section_code,
    section_index,
    cde_code,
):
    """
    Problem: If a user changes an input of a calculated field which sits on
    another form, the calculation will not be re-evaluated unless
    they go that form and save.
    This task recalculates a calculated cde automatically.
    The task is spawn in the postsave of the form with the changed input
    """
    from rdrf.models.definition.models import Registry
    from rdrf.models.definition.models import CommonDataElement
    from rdrf.models.definition.models import RDRFContext
    from rdrf.forms.fields import calculated_functions as cf
    from registry.patients.models import Patient

    what = f"{registry_code}/{form_name}/{section_index}/{section_code}/{cde_code}"
    msg = f"recalc of {what} in context {context_id}"
    logger.info(msg)

    registry: Registry = Registry.objects.get(code=registry_code)

    if not registry.has_feature("use_new_style_calcs"):
        logger.info(
            "recalc: will not recalculate cde as registry not using new style calcs feature"
        )
        return

    cde_model = CommonDataElement.objects.get(code=cde_code)
    if cde_model.datatype != "calculated":
        logger.error(
            f"cannot recalculate cde {cde_code} as it is not a calculated field"
        )
        return

    calculation_func = getattr(cf, cde_code)
    if not callable(calculation_func):
        logger.error(f"could not find calculation for {cde_code}")
        return

    inputs_func_name = f"{cde_code}_inputs"
    get_input_cde_codes_func = getattr(cf, inputs_func_name)
    if not callable(get_input_cde_codes_func):
        logger.error(f"could not find inputs for {cde_code}")
        return

    def get_patient_dict(patient_model):
        return {"patient_id": patient_model.id, "registry_code": registry.code}

    patient_model = Patient.objects.get(id=patient_id)
    patient_dict = get_patient_dict(patient_model)

    patient_contexts = patient_model.context_models
    ids = [c.id for c in patient_contexts]
    if context_id not in ids:
        logger.error("recalc not possible in passed in context")
        return

    context_model = RDRFContext.objects.get(id=context_id)

    patient_data = patient_model.get_dynamic_data(registry, context_id=context_id)

    def get_input_value(cde_code):
        for form_dict in patient_data["forms"]:
            for section_dict in form_dict["sections"]:
                if not section_dict["allow_multiple"]:
                    for cde_dict in section_dict["cdes"]:
                        if cde_dict["code"] == cde_code:
                            value = cde_dict["value"]
                            return value

    def save_result(result):
        patient_model.set_form_value(
            registry_code, form_name, section_code, cde_code, result, context_model
        )
        logger.info("recalc successful")

    input_cde_codes = get_input_cde_codes_func()
    input_context = {}
    for input_cde_code in input_cde_codes:
        input_value = get_input_value(input_cde_code)
        input_context[input_cde_code] = input_value

    try:
        updated_result = calculation_func(patient_dict, input_context)
    except Exception as ex:
        logger.info(f"error recalculating {cde_code}: {ex}")
        updated_result = ""

    # now save the result
    save_result(updated_result)
    logger.info(f"DONE {msg} new value = [{updated_result}]")


logger.info("registered tasks")


@app.task(name="rdrf.services.tasks.send_proms_request")
def send_proms_request(registry_code, patient_id, survey_name=None, form_name=None):
    from rdrf.models.definition.models import Registry
    from rdrf.models.definition.models import RegistryForm
    from registry.patients.models import Patient
    from rdrf.models.proms.models import SurveyRequest
    from rdrf.models.proms.models import Survey
    from rdrf.models.proms.models import SurveyRequestStates
    from rdrf.helpers.utils import generate_token

    logger.info(f"sending proms request patient {patient_id} {survey_name} {form_name}")

    patient_token = generate_token()
    logger.info(f"patient token {patient_token}")
    user = "admin"
    registry_model = Registry.objects.get(code=registry_code)
    patient_model = Patient.objects.get(id=patient_id)
    communication_type = "email"

    if survey_name is None:
        if form_name is None:
            raise Exception("send_proms_request_task needs survey_name or form_name")
        form_model = RegistryForm.objects.get(registry=registry_model, name=form_name)
        survey = Survey.objects.get(registry=registry_model, form=form_model)
        survey_name = survey.name

    survey_request = SurveyRequest(
        survey_name=survey_name,
        registry=registry_model,
        patient=patient_model,
        user=user,
        state=SurveyRequestStates.REQUESTED,
        patient_token=patient_token,
        communication_type=communication_type,
    )

    survey_request.save()
    logger.info("saved survey_request ok")
    try:
        survey_request.send()
    except Exception as ex:
        logger.error(f"Error sending: {ex}")


@app.task(name="rdrf.services.tasks.check_proms")
def check_proms(registry_code, pid):
    from rdrf.models.definition.models import Registry
    from registry.patients.models import Patient
    from rdrf.scheduling.scheduling import PromsDataAnalyser, PromsAction
    from rdrf.helpers.utils import has_died

    registry = Registry.objects.get(code=registry_code)
    patient = Patient.objects.get(id=pid)
    logger.debug(f"check_proms task for {registry_code} {pid}")

    if has_died(patient):
        logger.debug("patient has died so won't be sent proms requests")
        return

    logger.debug(f"analysing proms for {pid}")
    proms_data_analyser = PromsDataAnalyser(registry, patient)

    actions: list[PromsAction] = proms_data_analyser.analyse()

    for action in actions:
        logger.debug(f"spawning action {action.action_name} for {pid}...")
        if action.action_name == "send_proms_request":
            send_proms_request.delay(
                action.registry.code, action.patient.id, None, action.form
            )
