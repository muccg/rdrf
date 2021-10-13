from rdrf.celery import app
from intframework.utils import get_event_code
from intframework.updater import HL7Handler
import hl7

import logging

logger = logging.getLogger(__name__)


@app.task(name="rdrf.services.tasks.run_custom_action")
def run_custom_action(custom_action_id, user_id, patient_id, input_data):
    logger.debug("running custom action %s async" % custom_action_id)
    logger.debug("user_id = %s" % user_id)
    logger.debug("patient_id = %s" % patient_id)
    logger.debug("input_data = %s" % input_data)
    from rdrf.models.definition.models import CustomAction
    from registry.groups.models import CustomUser
    from registry.patients.models import Patient

    if patient_id != 0:
        patient_model = Patient.objects.get(id=patient_id)
    else:
        patient_model = None

    logger.debug("patient model = %s" % patient_model)

    user = CustomUser.objects.get(id=user_id)
    logger.debug("user = %s" % user)
    custom_action = CustomAction.objects.get(id=custom_action_id)

    logger.debug("running custom action execute")
    return custom_action.execute(user, patient_model, input_data)


@app.task(name="rdrf.services.tasks.handle_hl7_message")
def handle_hl7_message(umrn, message: hl7.Message):
    logger.info(f"running handle hl7 message task for {umrn} {message}")
    logger.info(f"type of message = {type(message)}")
    event_code = get_event_code(message)
    logger.info(f"HL7 Message {event_code} for UMRM: {umrn}")
    hl7_handler = HL7Handler(umrn=umrn, hl7message=message)
    response_data = hl7_handler.handle()


def testtask(num):
    logger.info(f"testtask called with num={num}")
    return 23 + num
