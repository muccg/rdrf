from django.http import HttpResponse
from django.views.generic import TemplateView, ListView
from django.core.urlresolvers import reverse_lazy
from django.forms import ModelForm
from django.views.generic.base import View
from django.shortcuts import render_to_response, RequestContext
from django.views.generic.base import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.http import Http404
from django.contrib.contenttypes.models import ContentType

from rdrf.models import Registry
from rdrf.models import RDRFContext
from rdrf.models import ContextFormGroup
from rdrf.utils import get_error_messages
from rdrf.utils import get_form_links
from rdrf.locators import PatientLocator
from rdrf.components import RDRFContextLauncherComponent

from registry.patients.models import Patient
from registry.groups.models import WorkingGroup

import logging

logger = logging.getLogger("registry_log")


class ContextForm(ModelForm):

    class Meta:
        model = RDRFContext
        fields = ['display_name']


class ContextFormGroupHelperMixin(object):

    def get_context_form_group(self, form_group_id):
        if form_group_id is None:
            return None
        else:
            return ContextFormGroup.objects.get(pk=form_group_id)

    def get_context_name(self, registry_model, context_form_group):
        if not registry_model.has_feature("contexts"):
            raise Exception("Registry does not support contexts")
        else:
            if context_form_group is not None:
                return context_form_group.name
            else:
                return registry_model.metadata.get("context_name", "Context")

    def get_context_launcher(self, user, registry_model, patient_model, context_model=None):
        context_launcher = RDRFContextLauncherComponent(user,
                                                        registry_model,
                                                        patient_model,
                                                        '',
                                                        context_model)

        return context_launcher.html

    def get_naming_info(self, form_group_id):
        if form_group_id is not None:
            context_form_group = ContextFormGroup.objects.get(id=form_group_id)
            return context_form_group.naming_info
        else:
            return "Display Name will default to 'Modules' if left blank"

    def get_default_name(self, patient_model, context_form_group_model):
        if context_form_group_model is None:
            return "Modules"
        else:
            return context_form_group_model.get_default_name(patient_model)

    def allowed(self, user, registry_code, patient_id, context_id):
        try:
            is_normal_user = not user.is_superuser
            registry_model = Registry.objects.get(code=registry_code)
            if not registry_model.has_feature("contexts"):
                return False
            patient_model = Patient.objects.get(pk=patient_id)
            patient_working_groups = set([wg for wg in patient_model.working_groups.all()])
            context_model = RDRFContext.objects.get(pk=context_id)
            if not user.is_superuser:
                user_working_groups = set([wg for wg in user.working_groups.all()])
            else:
                user_working_groups = set([wg for wg in WorkingGroup.objects.filter(registry=registry_model)])

            if is_normal_user and not user.in_registry(registry_model):
                return False
            if context_model.registry.code != registry_model.code:
                return False
            if not (patient_working_groups <= user_working_groups):
                return False
            return True
        except Exception, ex:
            logger.error("error in context allowed check: %s" % ex)
            return False

    def sanity_check(self, registry_model):
        if not registry_model.has_feature("contexts"):
            return HttpResponseRedirect("/")

    def create_context_and_goto_form(self, registry_model, patient_model, context_form_group):
        assert len(context_form_group.form_models) == 1, "Direct link only possible if num forms in form group is 1"
        patient_content_type = ContentType.objects.get_for_model(patient_model)
        form_model = context_form_group.form_models[0]
        context_model = RDRFContext()
        context_model.registry = registry_model
        context_model.name = "change me"
        context_model.content_object = patient_model
        context_model.content_type = patient_content_type
        context_model.context_form_group = context_form_group

        context_model.save()
        form_link = reverse('registry_form', args=(registry_model.code,
                                                   form_model.id,
                                                   patient_model.pk,
                                                   context_model.id))

        return HttpResponseRedirect(form_link)


class RDRFContextCreateView(View, ContextFormGroupHelperMixin):
    model = RDRFContext

    template_name = "rdrf_cdes/rdrf_context.html"
    success_url = reverse_lazy('contextslisting')

    @method_decorator(login_required)
    def get(self, request, registry_code, patient_id, context_form_group_id=None):
        registry_model = Registry.objects.get(code=registry_code)
        self.sanity_check(registry_model)
        patient_model = Patient.objects.get(pk=patient_id)
        context_form_group = self.get_context_form_group(context_form_group_id)
        naming_info = self.get_naming_info(context_form_group_id)

        context_name = self.get_context_name(registry_model, context_form_group)
        default_display_name = self.get_default_name(patient_model, context_form_group)
        default_values = {"display_name": default_display_name}

        if context_form_group and context_form_group.supports_direct_linking:
            return self.create_context_and_goto_form(registry_model,
                                                     patient_model,
                                                     context_form_group)

        context = {"location": "Add %s" % context_name,
                   "registry": registry_model.code,
                   "patient_id": patient_id,
                   "form_links": [],
                   "context_name": context_name,
                   'patient_link': PatientLocator(registry_model, patient_model).link,
                   "patient_name": patient_model.display_name,
                   "context_launcher": self.get_context_launcher(request.user,
                                                                 registry_model,
                                                                 patient_model),
                   "naming_info": naming_info,
                   "form": ContextForm(initial=default_values)}

        return render_to_response(
            "rdrf_cdes/rdrf_context.html",
            context,
            context_instance=RequestContext(request))

    @method_decorator(login_required)
    def post(self, request, registry_code, patient_id, context_form_group_id=None):
        form = ContextForm(request.POST)
        registry_model = Registry.objects.get(code=registry_code)
        self.sanity_check(registry_model)
        patient_model = Patient.objects.get(pk=patient_id)
        context_form_group_model = self.get_context_form_group(context_form_group_id)
        naming_info = self.get_naming_info(context_form_group_id)
        context_name = self.get_context_name(registry_model, context_form_group_model)

        if form.is_valid():
            patient_model = Patient.objects.get(id=patient_id)
            registry_model = Registry.objects.get(code=registry_code)
            content_type = ContentType.objects.get_for_model(patient_model)
            context_model = form.save(commit=False)
            context_model.registry = registry_model
            context_model.content_type = content_type
            context_model.content_object = patient_model
            if context_form_group_model:
                context_model.context_form_group = context_form_group_model

            context_model.save()
            cfg_id = context_form_group_model.pk if context_form_group_model else None
            context_edit = reverse('context_edit', kwargs={"registry_code": registry_model.code,
                                                           "patient_id": patient_model.pk,
                                                           "context_id": context_model.pk})

            return HttpResponseRedirect(context_edit)
        else:
            error_messages = get_error_messages([form])
            context = {"location": "Add %s" % context_name,
                       "errors": True,
                       "error_messages": error_messages,
                       "registry": registry_model.code,
                       'patient_link': PatientLocator(registry_model, patient_model).link,
                       "patient_id": patient_id,
                       "form_links": [],
                       "naming_info": naming_info,
                       "context_launcher": self.get_context_launcher(request.user,
                                                                     registry_model,
                                                                     patient_model),
                       "patient_name": patient_model.display_name,
                       "form": ContextForm(request.POST)}

        return render_to_response(
            "rdrf_cdes/rdrf_context.html",
            context,
            context_instance=RequestContext(request))


class RDRFContextEditView(View, ContextFormGroupHelperMixin):
    model = RDRFContext
    template_name = "rdrf_cdes/rdrf_context.html"
    success_url = reverse_lazy('contextslisting')

    @method_decorator(login_required)
    def get(self, request, registry_code, patient_id, context_id):
        try:
            rdrf_context_model = RDRFContext.objects.get(pk=context_id)
        except RDRFContext.DoesNotExist:
            raise Http404()

        if not self.allowed(request.user, registry_code, patient_id, context_id):
            return HttpResponseRedirect("/")

        context_form = ContextForm(instance=rdrf_context_model)

        patient_model = rdrf_context_model.content_object
        registry_model = rdrf_context_model.registry
        patient_name = patient_model.display_name
        if rdrf_context_model.context_form_group:
            context_form_group_model = self.get_context_form_group(rdrf_context_model.context_form_group.pk)
            naming_info = context_form_group_model.naming_info
        else:
            context_form_group_model = None
            naming_info = self.get_naming_info(None)

        context_name = self.get_context_name(registry_model, context_form_group_model)

        form_links = get_form_links(request.user,
                                    rdrf_context_model.object_id,
                                    rdrf_context_model.registry,
                                    rdrf_context_model,
                                    )

        context = {"location": "Edit %s" % context_name,
                   "context_id": context_id,
                   "patient_name": patient_name,
                   "form_links": form_links,
                   'patient_link': PatientLocator(registry_model, patient_model).link,
                   "context_launcher": self.get_context_launcher(request.user,
                                                                 registry_model,
                                                                 patient_model),
                   "context_name": context_name,
                   "registry": registry_model.code,
                   "naming_info": naming_info,
                   "patient_id": patient_id,
                   "form": context_form}

        return render_to_response(
            "rdrf_cdes/rdrf_context.html",
            context,
            context_instance=RequestContext(request))

    @method_decorator(login_required)
    def post(self, request, registry_code, patient_id, context_id):
        registry_model = Registry.objects.get(code=registry_code)
        context_model = RDRFContext.objects.get(pk=context_id)
        context_form_group_model = context_model.context_form_group
        if context_form_group_model:
            naming_info = context_form_group_model.naming_info
        else:
            naming_info = self.get_naming_info(None)
        context_name = context_model.registry.metadata.get("context_name", "Context")
        patient_model = Patient.objects.get(id=patient_id)
        form = ContextForm(request.POST, instance=context_model)

        if form.is_valid():
            content_type = ContentType.objects.get_for_model(patient_model)
            context_model = form.save(commit=False)
            context_model.registry = registry_model
            context_model.content_type = content_type
            context_model.content_object = patient_model
            context_model.save()
            form_links = get_form_links(request.user,
                                        context_model.object_id,
                                        context_model.registry,
                                        context_model)

            context = {"location": "Edit %s" % context_name,
                       "patient_name": patient_model.display_name,
                       'patient_link': PatientLocator(registry_model, patient_model).link,
                       "form_links": form_links,
                       "context_launcher": self.get_context_launcher(request.user,
                                                                     registry_model,
                                                                     patient_model),
                       "message": "%s saved successfully" % context_name,
                       "error_messages": [],
                       "registry": registry_model.code,
                       "naming_info": naming_info,
                       "patient_id": patient_id,
                       "form": ContextForm(instance=context_model),
                       }

        else:

            error_messages = get_error_messages([form])

            context = {"location": "Add %s" % context_name,
                       "errors": True,
                       "error_messages": error_messages,
                       "registry": registry_model.code,
                       "patient_id": patient_id,
                       "form_links": [],
                       'patient_link': PatientLocator(registry_model, patient_model).link,
                       "context_launcher": self.get_context_launcher(request.user,
                                                                     registry_model,
                                                                     patient_model),
                       "error_messages": error_messages,
                       "naming_info": naming_info,
                       "patient_name": patient_model.display_name,
                       "form": ContextForm(request.POST)}

        return render_to_response(
            "rdrf_cdes/rdrf_context.html",
            context,
            context_instance=RequestContext(request))
