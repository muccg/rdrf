from django.shortcuts import render_to_response
from django.views.generic.base import View
from django.core.context_processors import csrf
from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages
from django.template import RequestContext
from django.forms.formsets import formset_factory

import logging

from models import RegistryForm
from models import Section
from registry.patients.models import Patient

from dynamic_forms import create_form_class_for_section
from dynamic_data import DynamicDataWrapper

logger = logging.getLogger("registry_log")

class FormView(View):

    def get(self, request, registry_code, form_id, patient_id):
        patient = Patient.objects.get(pk=patient_id)
        dyn_patient = DynamicDataWrapper(patient)

        dynamic_data = dyn_patient.load_dynamic_data(registry_code,"cdes")

        form_obj = self.get_registry_form(form_id)
        
        sections, display_names = self._get_sections(form_obj)

        form_section = {}
        section_element_map = {}
        for s in sections:
            form_class = create_form_class_for_section(s)
            section_model = Section.objects.get(code=s)
            section_elements = section_model.get_elements()
            section_element_map[s] = section_elements
            if not section_model.allow_multiple:
                # return a normal form
                form_section[s] = form_class(dynamic_data)
            else:
                # return a formset
                if section_model.extra:
                    extra = section_model.extra
                else:
                    extra = 0
                form_set_class = formset_factory(form_class, extra=extra)
                initial_data = [dynamic_data]
                form_section[s]  = form_set_class(initial=initial_data)
        
        context = {
            'registry': registry_code,
            'form_name': form_id,
            'patient_id': patient_id,
            'patient_name': '%s %s' % (patient.given_names, patient.family_name),
            'sections': sections,
            'display_names': display_names,
            'forms': form_section,
            'section_element_map': section_element_map,
        }
        context.update(csrf(request))
        return render_to_response('rdrf_cdes/form.html', context)

    def post(self, request, registry_code, form_id, patient_id):
        patient = Patient.objects.get(pk=patient_id)
        dyn_patient = DynamicDataWrapper(patient)
        form_obj = self.get_registry_form(form_id)
        sections, display_names = self._get_sections(form_obj)
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
                for e in form.errors:
                    logger.debug("Validation error on form: %s" % e)

            form_section[s] = form_class(request.POST)

        patient_name = '%s %s' % (patient.given_names, patient.family_name)

        context = {
            'registry': registry_code,
            'form_name': form_id,
            'patient_id': patient_id,
            'patient_name': patient_name,
            'sections': sections,
            'forms': form_section,
            'display_names': display_names
        }

        context.update(csrf(request))
        messages.add_message(request, messages.INFO, 'Patient %s saved successfully' % patient_name)
        return render_to_response('rdrf_cdes/form.html', context, context_instance=RequestContext(request))


    def _get_sections(self, form):
        section_parts = form.sections.split(",")        
        sections = []
        display_names = {}
        for s in section_parts:
            try:
                sec = Section.objects.get(code=s.strip())
                display_names[s] = sec.display_name
                sections.append(s)
            except ObjectDoesNotExist:
                logger.error("Section %s does not exist" % s)
        return sections, display_names
    
    def get_registry_form(self, form_id):
        return RegistryForm.objects.get(id=form_id)