from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect
from django.http import Http404
from django.conf import settings
from django.template.context_processors import csrf
from dynamic_forms import create_form_class
from dynamic_data import DynamicDataWrapper
from django.views.generic import View
from django.http import HttpResponse
from django.utils.translation import ugettext as _

from models import Registry
import json


class AllocateView(View):

    def get(self, request):
        regs = Registry.objects.all()
        print regs
        results = [obj.as_json() for obj in regs]
        return HttpResponse(json.dumps(results), content_type='application/json')


class RegistryList(View):

    def get(self, request):
        regs = Registry.objects.all()
        print regs
        results = [obj.as_json() for obj in regs]
        return HttpResponse(json.dumps(results), content_type='application/json')


def patient_cdes(request, patient_id):
    owner_model_func = settings.CDE_MODEL_MAP["Patient"]
    owner_model = owner_model_func()  # a Model _class_

    try:
        patient = owner_model.objects.get(pk=patient_id)
        dyn_patient = DynamicDataWrapper(patient)

    except owner_model.DoesNotExist:
        raise Http404(_("Patient does not exist"))

    form_class = create_form_class('Patient')

    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            dyn_patient.save_dynamic_data("dmd", "cdes", form.cleaned_data)
            return HttpResponseRedirect('/cdes/patient/%s' % patient_id)
    else:
        form = form_class(dyn_patient.load_dynamic_data("dmd", "cdes"))

    context = {'form': form, 'owner': 'patient',
               'owner_id': patient_id,
               'name': patient.given_names + " " + patient.family_name}

    context.update(csrf(request))

    return render_to_response('rdrf_cdes/cde.html', context)
