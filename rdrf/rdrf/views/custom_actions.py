from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.views.generic.base import View
from django.template.context_processors import csrf
from django.http import Http404
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from rdrf.models.definition.models import CustomAction
from registry.patients.models import Patient
import logging

logger = logging.getLogger(__name__)


class CustomActionView(View):
    @method_decorator(login_required)
    def get(self, request, action_id, patient_id):
        user = request.user
        custom_action = get_object_or_404(CustomAction, id=action_id)
        requires_patient = custom_action.scope != "U"
        requires_gui = custom_action.requires_input
        is_asynchronous = custom_action.asynchronous

        if requires_patient:
            patient_model = get_object_or_404(Patient, id=patient_id)
        else:
            patient_model = None

        if requires_gui:
            return self._generate_gui(request, custom_action)
        elif is_asynchronous:
            return self._polling_view(user,
                                      custom_action,
                                      patient_model)
        else:
            return custom_action.execute(user, patient_model)

    def _generate_gui(self,
                      request,
                      custom_action):
        input_form = custom_action.input_form_class()
        template_context = {
            "custom_action": custom_action,
            "input_form": input_form,
        }
        template_context.update(csrf(request))
        template = "rdrf_cdes/custom_action_input_form.html"
        return render(request, template, template_context)

    @method_decorator(login_required)
    def post(self, request, action_id, patient_id):
        logger.debug("received post of action")
        user = request.user
        custom_action = get_object_or_404(CustomAction, id=action_id)
        if not custom_action.requires_input:
            raise Http404

        if patient_id != "":
            patient_model = get_object_or_404(Patient, id=patient_id)
        else:
            patient_model = None

        input_form = custom_action.input_form_class(request.POST)
        if not input_form.is_valid():
            raise Exception("not valid")
        input_data = input_form.cleaned_data
        logger.debug("input data = %s" % input_data)

        # execute async
        if custom_action.asynchronous:
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
