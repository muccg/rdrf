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
        logger.debug("user = %s" % self.user)

    def run(self):
        logger.debug("action = %s" % self.command)
        if self.command == "form":
            logger.debug("action is form")
            return self._process_form()
        elif self.command == "survey":
            logger.debug("processing survey")
            return self._process_survey()
        else:
            logger.debug("unknown action: %s" % self.command)
            raise Http404

    def _parse_command(self):
        return self.request.GET.get("action")

    def _get_field(self, field):
        value = self.request.GET.get(field)
        logger.debug("field = %s value = %s" % (field, value))
        return value

    def _get_patient(self):
        from registry.patients.models import Patient
        from registry.patients.models import ParentGuardian
        if "id"in self.request.GET:
            try:
                patient_model = Patient.objects.get(id=self.request.GET.get("id"))
                if not is_authorised(self.user, patient_model):
                    logger.debug("action not authorised")
                    raise PermissionError
                else:
                    logger.debug("patient found by id ok")
                    return patient_model

            except Patient.DoesNotExist:
                logger.debug("patient does not exist")
                raise Http404

        try:
            logger.debug("patient id not supplied , finding patient assoc with user..")
            patient_model = Patient.objects.filter(user=self.user).order_by("id").first()
            if patient_model is not None:
                logger.debug("found patient associated with user %s" % patient_model)
                return patient_model
        except Patient.DoesNotExist:
            logger.debug("user is not a patient ...")
            pass

        try:
            logger.debug("trying parents ... ")
            parent = ParentGuardian.objects.get(user=self.user)
            # what to do if there is more than one child
            # for now we take the first
            children = parent.children
            if children:
                logger.debug("parent guardian found and no id - returning first child")
                return children[0]
            else:
                logger.debug("user is a parent but has not children??? ...")
                raise Http404
        except ParentGuardian.DoesNotExist:
            logger.debug("no parent guardian assoc with user ...")
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
        if patient_model is not None:
            logger.debug("determined patient")
        else:
            logger.debug("patient is None??")
            raise PermissionDenied

        if not patient_model.in_registry(registry_model.code):
            logger.debug("patient not in registry supplied")
            raise PermissionDenied

        from rdrf.helpers.utils import FormLink
        default_context = patient_model.default_context(registry_model)
        form_link = FormLink(patient_model.id,
                             registry_model,
                             form_model,
                             context_model=default_context)
        logger.debug("found form link for universal link")
        return HttpResponseRedirect(form_link.url)


class ActionExecutorView(View):
    @method_decorator(login_required)
    def get(self, request):
        logger.debug("actions request")
        action = Action(request)
        return action.run()
