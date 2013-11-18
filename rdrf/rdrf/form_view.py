from django.shortcuts import render_to_response
from django.views.generic.base import View
from django.core.context_processors import csrf
from django.core.exceptions import ObjectDoesNotExist
import logging

from models import RegistryForm
from models import Section
from registry.patients.models import Patient

from dynamic_forms import create_form_class_for_section
from dynamic_data import DynamicDataWrapper

logger = logging.getLogger("dmd")

class FormView(View):

    def get(self, request, registry_code, form_name, patient_id):
        patient = Patient.objects.get(pk=patient_id)
        dyn_patient = DynamicDataWrapper(patient)

        dynamic_data = dyn_patient.load_dynamic_data(registry_code,"cdes")

        form_obj = RegistryForm.objects.get(name=form_name)
        
        sections = self._get_sections(form_obj)
        
        form_section = {}
        for s in sections:
            form_section[s] =   create_form_class_for_section(s)
        
        context = {
            'registry': form_obj.registry,
            'form_name': form_name,
            'patient_id': patient_id,
            'sections': sections,
            'forms': form_section
        }
        context.update(csrf(request))
        
        print context
        
        return render_to_response('rdrf_cdes/form.html', context)

    def post(self, request, form_name, patient_id):
        patient = Patient.objects.get(pk=patient_id)
        dyn_patient = DynamicDataWrapper(patient)

        return render_to_response('rdrf_cdes/form.html')
    
    def _get_sections(self, form):
        section_parts = form.sections.split(",")        
        sections = []
        for s in section_parts:
            try:
                Section.objects.get(code=s)
                sections.append(s)
            except ObjectDoesNotExist:
                logger.error("Section %s does not exist" % s)
        return sections