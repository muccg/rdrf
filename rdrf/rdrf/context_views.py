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

from registry.patients.models import Patient


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

                


class RDRFContextCreateView(View, ContextFormGroupHelperMixin):
    model = RDRFContext

    template_name = "rdrf_cdes/rdrf_context.html"
    success_url = reverse_lazy('contextslisting')

    @method_decorator(login_required)
    def get(self, request, registry_code, patient_id, context_form_group_id=None):
        registry_model = Registry.objects.get(code=registry_code)
        patient_model = Patient.objects.get(pk=patient_id)
        context_form_group = self.get_context_form_group(context_form_group_id)
        if not registry_model.has_feature("contexts"):
            return HttpResponseRedirect("/")

        context_name = self.get_context_name(registry_model, context_form_group)
        

        context = {"location": "Add %s" % context_name,
                   "registry": registry_model.code,
                   "patient_id": patient_id,
                   "my_contexts_url": patient_model.get_contexts_url(registry_model),
                   "patient_name": patient_model.display_name,
                   "form_links": [],
                   "my_contexts_url": patient_model.get_contexts_url(registry_model),
                   "form": ContextForm}

        return render_to_response(
            "rdrf_cdes/rdrf_context.html",
            context,
            context_instance=RequestContext(request))


    def post(self, request, registry_code, patient_id, context_form_group_id=None):
        form = ContextForm(request.POST)
        registry_model = Registry.objects.get(code=registry_code)
        patient_model = Patient.objects.get(pk=patient_id)
        context_form_group_model = self.get_context_form_group(context_form_group_id)
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
            context = {"location": "Add %s" % context_name,
                       "error": "Invalid",
                       "registry": registry_model.code,
                       "patient_id": patient_id,
                       "my_contexts_url": patient_model.get_contexts_url(registry_model),
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

        if not self._allowed(request.user, registry_code, patient_id, context_id):
            return HttpResponseRedirect("/")

        context_form = ContextForm(instance=rdrf_context_model)

        context_name = rdrf_context_model.registry.metadata.get("context_name", "Context")
        patient_model = rdrf_context_model.content_object
        registry_model = rdrf_context_model.registry
        patient_name = patient_model.display_name

        form_links = get_form_links(request.user,
                                    rdrf_context_model.object_id,
                                    rdrf_context_model.registry,
                                    rdrf_context_model,
                                    )

        context = {"location": "Edit %s" % context_name,
                   "context_id": context_id,
                   "patient_name": patient_name,
                   "my_contexts_url": patient_model.get_contexts_url(registry_model),
                   "context_name": context_name,
                   "form_links": form_links,
                   "registry": registry_model.code,
                   "patient_id": patient_id,
                   "form": context_form}

        return render_to_response(
            "rdrf_cdes/rdrf_context.html",
            context,
            context_instance=RequestContext(request))

    def _allowed(self, user, registry_code, patient_id, context_id):
        return True #todo - do security check

    def post(self, request, registry_code, patient_id, context_id):
        registry_model = Registry.objects.get(code=registry_code)
        context_model = RDRFContext.objects.get(pk=context_id)
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
                                        patient_model.pk,
                                        registry_model,
                                        context_model)

            context = {"location": "Edit %s" % context_name,
                       "patient_name": patient_model.display_name,
                       "my_contexts_url": patient_model.get_contexts_url(registry_model),
                       "message": "%s saved successfully" % context_name,
                       "error_messages": [],
                       "registry": registry_model.code,
                       "patient_id": patient_id,
                       "form_links": form_links,
                       "form": form}

        else:

            error_messages = get_error_messages([form])

            context = {"location": "Add %s" % context_name,
                       "errors": True,
                       "registry": registry_model.code,
                       "patient_id": patient_id,
                       "error_messages": error_messages,
                       "form_links": [],
                       "patient_name": patient_model.display_name,
                       "form": ContextForm(request.POST)}

        return render_to_response(
            "rdrf_cdes/rdrf_context.html",
            context,
            context_instance=RequestContext(request))

