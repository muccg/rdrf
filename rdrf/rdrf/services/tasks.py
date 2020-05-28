from celery import shared_task


@shared_task
def run_custom_action(custom_action_id, user_id, patient_id, input_data):
    from rdrf.models.definition.models import CustomAction
    from registry.groups.models import CustomUser
    from registry.patients.models import Patient

    if patient_id != 0:
        patient_model = Patient.objects.get(id=patient_id)
    else:
        patient_model = None

    user = CustomUser.objects.get(id=user_id)
    custom_action = CustomAction.ojjects.get(id=custom_action_id)

    custom_action.execute(user, patient_model, input_data)
