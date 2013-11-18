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

logger = logging.getLogger("registry_log")

class FormView(View):

    def get(self, request, registry_code, form_name, patient_id):
        patient = Patient.objects.get(pk=patient_id)
        dyn_patient = DynamicDataWrapper(patient)

        dynamic_data = dyn_patient.load_dynamic_data(registry_code,"cdes")

        form_obj = RegistryForm.objects.get(name=form_name, registry=registry_code)
        
        sections = self._get_sections(form_obj)
        
        form_section = {}
        for s in sections:
            form_section[s] =   create_form_class_for_section(s)
        
        context = {
            'registry': registry_code,
            'form_name': form_name,
            'patient_id': patient_id,
            'sections': sections,
            'forms': form_section
        }
        context.update(csrf(request))
        return render_to_response('rdrf_cdes/form.html', context)

    def post(self, request, registry_code, form_name, patient_id):
        patient = Patient.objects.get(pk=patient_id)
        dyn_patient = DynamicDataWrapper(patient)
        form_obj = RegistryForm.objects.get(name=form_name, registry=registry_code)
        sections = self._get_sections(form_obj)
        form_section = {}
        for s in sections:
            form_class = create_form_class_for_section(s)
            logger.debug("created form class for section %s: %s" % (s, form_class))
            logger.debug("POST data = %s" % request.POST)
            form = form_class(request.POST)
            if form.is_valid():
                logger.debug("form is valid")
                dynamic_data = form.cleaned_data
                dyn_patient.save_dynamic_data(registry_code, "cdes", dynamic_data)
            else:


            form_section[s] = form



        context = {
            'registry': registry_code,
            'form_name': form_name,
            'patient_id': patient_id,
            'sections': sections,
            'forms': form_section
        }

        context.update(csrf(request))
        return render_to_response('rdrf_cdes/form.html', context)
    
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