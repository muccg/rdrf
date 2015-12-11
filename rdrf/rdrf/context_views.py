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
from registry.patients.models import Patient


class ContextForm(ModelForm):
    class Meta:
        model = RDRFContext
        fields = ['display_name']


class RDRFContextCreateView(View):
    model = RDRFContext

    template_name = "rdrf_cdes/rdrf_context.html"
    success_url = reverse_lazy('contextslisting')

    @method_decorator(login_required)
    def get(self, request, registry_code, patient_id):
        registry_model = Registry.objects.get(code=registry_code)
        patient_model = Patient.objects.get(pk=patient_id)
        if not registry_model.has_feature("contexts"):
            return HttpResponseRedirect("/")

        context_name = registry_model.metadata.get("context_name", "Context")

        context = {"location": "Add %s" % context_name,
                   "patient_name": patient_model.display_name,
                   "form": ContextForm}

        return render_to_response(
            "rdrf_cdes/rdrf_context.html",
            context,
            context_instance=RequestContext(request))

    def post(self, request, registry_code, patient_id):
        form = ContextForm(request.POST)
        registry_model = Registry.objects.get(code=registry_code)
        context_name = registry_model.metadata.get("context_name", "Context")
        if form.is_valid():
            patient_model = Patient.objects.get(id=patient_id)
            registry_model = Registry.objects.get(code=registry_code)
            content_type = ContentType.objects.get_for_model(patient_model)
            context_model = form.save(commit=False)
            context_model.registry = registry_model
            context_model.content_type = content_type
            context_model.content_object = patient_model
            context_model.save()
            context_edit = reverse('context_edit', kwargs={"registry_code": registry_model.code,
                                                           "patient_id": patient_model.pk,
                                                           "context_id": context_model.pk})
            return HttpResponseRedirect(context_edit)
        else:
            context = {"location": "Add %s" % context_name,
                       "error": "Invalid",
                       "patient_name": patient_model.display_name,
                       "form": ContextForm(request.POST)}

        return render_to_response(
            "rdrf_cdes/rdrf_context.html",
            context,
            context_instance=RequestContext(request))


class RDRFContextEditView(View):
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
        patient_name = rdrf_context_model.content_object.display_name

        context = {"location": "Edit %s" % context_name,
                   "patient_name": patient_name,
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
            context = {"location": "Edit %s" % context_name,
                       "patient_name": patient_model.display_name,
                       "form": form}

        else:
            context = {"location": "Add %s" % context_name,
                       "error": "Invalid",
                       "patient_name": patient_model.display_name,
                       "form": ContextForm(request.POST)}

        return render_to_response(
            "rdrf_cdes/rdrf_context.html",
            context,
            context_instance=RequestContext(request))






