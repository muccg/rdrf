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

        context_name = registry_model.metadata["context_name"]

        context = {"location": "Add %s" % context_name,
                   "patient_name": patient_model.display_name,
                   "form": ContextForm}

        return render_to_response(
            "rdrf_cdes/rdrf_context.html",
            context,
            context_instance=RequestContext(request))


class RDRFContextEditView(View):
    model = RDRFContext
    success_url = reverse_lazy('contextslisting')
    fields = ['name', 'ip', 'order']
