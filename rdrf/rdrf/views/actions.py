from django.http import HttpResponseRedirect
from django.views.generic.base import View
from django.http import Http404
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied

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
        else:
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
        try:
            return Patient.objects.filter(user=self.user).order_by("id").first()
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
                raise Http404
        except ParentGuardian.DoesNotExist:
            raise Http404

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
        if not patient_model.in_registry(registry_model):
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
