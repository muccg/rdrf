from django.http import HttpResponseRedirect
from django.views.generic.base import View
from django.http import Http404
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from rdrf.helpers.utils import is_authorised

import logging

logger = logging.getLogger(__name__)


class Action:
    def __init__(self, request):
        self.request = request
        self.command = self._parse_command()
        self.user = self.request.user

    def run(self):
        if self.command == "form":
            return self._process_form()
        elif self.command == "survey":
            return self._process_survey()
        else:
            raise Http404

    def _parse_command(self):
        return self.request.GET.get("action")

    def _get_field(self, field):
        value = self.request.GET.get(field)
        return value

    def _get_patient(self):
        from registry.patients.models import Patient
        from registry.patients.models import ParentGuardian
        if "id" in self.request.GET:
            patient_id = self.request.GET.get("id")
            try:
                patient_model = Patient.objects.get(id=patient_id)
                if not is_authorised(self.user, patient_model):
                    logger.warning(f"action not authorised for user:{self.user.id} on patient:{patient_model.id}")
                    raise PermissionError
                else:
                    return patient_model

            except Patient.DoesNotExist:
                logger.warning(f"patient id {patient_id} does not exist")
                raise Http404

        try:
            patient_model = Patient.objects.filter(user=self.user).order_by("id").first()
            if patient_model is not None:
                return patient_model
        except Patient.DoesNotExist:
            pass

        try:
            parent = ParentGuardian.objects.get(user=self.user)
            # what to do if there is more than one child
            # for now we take the first
            children = parent.children
            if children:
                return children[0]
            else:
                logger.warning(f"user {self.user.id} is a parent but has not children??? ...")
                raise Http404
        except ParentGuardian.DoesNotExist:
            logger.warning(f"no parent guardian assoc with user {self.user.id} ...")
            raise Http404

    def _process_survey(self):
        from rdrf.models.definition.models import Registry
        from rdrf.models.proms.models import SurveyRequest
        from rdrf.models.proms.models import SurveyRequestStates

        registry_code = self._get_field("registry")
        registry_model = get_object_or_404(Registry,
                                           code=registry_code)

        if not self.user.in_registry(registry_model):
            raise PermissionDenied

        patient_model = self._get_patient()

        if patient_model is None:
            raise PermissionDenied

        survey_name = self._get_field("name")

        try:
            qry = SurveyRequest.objects.filter(patient=patient_model,
                                               state=SurveyRequestStates.REQUESTED,
                                               registry=registry_model,
                                               survey_name=survey_name)
            last_request = qry.order_by("-created").first()
        except SurveyRequest.DoesNotExist:
            raise Http404

        return HttpResponseRedirect(last_request.email_link)

    def _process_form(self):
        from rdrf.models.definition.models import Registry
        from rdrf.models.definition.models import RegistryForm

        registry_code = self._get_field("registry")
        registry_model = get_object_or_404(Registry,
                                           code=registry_code)

        if not self.user.in_registry(registry_model):
            raise PermissionDenied

        form_name = self._get_field("form")

        form_model = get_object_or_404(RegistryForm,
                                       name=form_name,
                                       registry=registry_model)

        patient_model = self._get_patient()
        if patient_model is None:
            logger.warning("patient is None??")
            raise PermissionDenied

        if not patient_model.in_registry(registry_model.code):
            logger.warning(f"patient {patient_model.id} not in registry supplied")
            raise PermissionDenied

        from rdrf.helpers.utils import FormLink
        default_context = patient_model.default_context(registry_model)
        form_link = FormLink(patient_model.id,
                             registry_model,
                             form_model,
                             context_model=default_context)
        return HttpResponseRedirect(form_link.url)


class ActionExecutorView(View):
    @method_decorator(login_required)
    def get(self, request):
        action = Action(request)
        return action.run()
