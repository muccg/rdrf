from rdrf.models.definition.models import CustomAction
from registry.patients.models import Patient
from django.shortcuts import get_object_or_404
from django.views.generic.base import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
import logging

logger = logging.getLogger(__name__)


class CustomActionView(View):
    @method_decorator(login_required)
    def get(self, request, action_id, patient_id):
        logger.debug("in custom action view ...")
        user = request.user
        custom_action = get_object_or_404(CustomAction, id=action_id)
        if custom_action.scope == "U":
            # not applicable to a patient
            return custom_action.execute(user)
        logger.debug("got custom action")
        patient_model = get_object_or_404(Patient, id=patient_id)
        logger.debug("got patient")
        # NB the following checks security
        logger.debug("executing action ...")
        return custom_action.execute(user, patient_model)


class CustomActionGUI(View):
    @method_decorator(login_required)
    def get(self, request, action_id, patient_id):
        user = request.user
        custom_action = get_object_or_404(CustomAction, id=action_id)
        patient_model = get_object_or_404(Patient, id=patient_id)
        if custom_action.requires_input:
            return self._generate_gui(user,
                                      custom_action,
                                      patient_model)
        else:
            # start async
            task_id = None
            return self._polling_view(user,
                                      custom_action,
                                      task_id,
                                      patient_model)

    @method_decorator(login_required)
    def post(self, request, action_id, patient_id):
        user = request.user
        custom_action = get_object_or_404(CustomAction, id=action_id)
        patient_model = get_object_or_404(Patient, id=patient_id)
        input_form = self._get_input_form(request,
                                          custom_action)

        input_data = input_form.get_input_data()
        # execute async
        if custom_action.is_asynchronous:
            task_id = custom_action.run_async(user, patient_model, input_data)
            return self._polling_view(user,
                                      custom_action,
                                      task_id,
                                      patient_model)

        else:
            return custom_action.execute(user, patient_model, input_data)


class CustomActionWrapper:
    """
    Used to construct action links
    """

    def __init__(self, registry, user, custom_action, patient_model):
        self.registry = registry
        self.user = user
        self.custom_action = custom_action
        self.patient_model = patient_model
        self.valid = self._check_validity()

    @property
    def url(self):
        if self.valid:
            from django.urls import reverse
            return reverse("custom_action", args=[self.custom_action.pk,
                                                  self.patient_model.pk])
        else:
            logger.debug("not valid")
            return ""

    @property
    def text(self):
        return self.custom_action.text

    def _check_validity(self):
        return self.custom_action.check_security(self.user,
                                                 self.patient_model)
