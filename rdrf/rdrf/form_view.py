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
        form_display_name = form_obj.name

        sections, display_names = self._get_sections(form_obj)

        form_section = {}
        section_element_map = {}
        total_forms_ids = {}
        initial_forms_ids = {}
        formset_prefixes = {}

        for s in sections:
            form_class = create_form_class_for_section(s)
            section_model = Section.objects.get(code=s)
            section_elements = section_model.get_elements()
            section_element_map[s] = section_elements

            if not section_model.allow_multiple:
                # return a normal form
                form_section[s] = form_class(dynamic_data)
            else:
                # Ensure that we can have multiple formsets on the one page
                prefix="formset_%s" % s
                formset_prefixes[s] = prefix
                total_forms_ids[s] = "id_%s-TOTAL_FORMS" % prefix
                initial_forms_ids[s] = "id_%s-INITIAL_FORMS" % prefix

                # return a formset
                if section_model.extra:
                    extra = section_model.extra
                else:
                    extra = 0
                form_set_class = formset_factory(form_class, extra=extra)
                if dynamic_data:
                    try:
                        initial_data = dynamic_data[s]  # we grab the list of data items by section code not cde code
                        logger.debug("retrieved data for section %s OK" % s)
                    except KeyError, ke:
                        logger.error("patient %s section %s data could not be retrieved: %s" % (patient_id, s, ke))
                        initial_data = [""] * len(section_elements)
                else:
                    initial_data = [""] * len(section_elements)

                logger.debug("initial data for section %s = %s" % (s, initial_data))
                form_section[s]  = form_set_class(initial=initial_data, prefix=prefix)
        
        context = {
            'registry': registry_code,
            'form_name': form_id,
            'form_display_name': form_display_name,
            'patient_id': patient_id,
            'patient_name': '%s %s' % (patient.given_names, patient.family_name),
            'sections': sections,
            'display_names': display_names,
            'forms': form_section,
            'section_element_map': section_element_map,
            "total_forms_ids" : total_forms_ids,
            "initial_forms_ids" : initial_forms_ids,
            "formset_prefixes" : formset_prefixes,
        }
        context.update(csrf(request))
        return render_to_response('rdrf_cdes/form.html', context)


    def post(self, request, registry_code, form_id, patient_id):
        patient = Patient.objects.get(pk=patient_id)
        dyn_patient = DynamicDataWrapper(patient)
        form_obj = self.get_registry_form(form_id)
        form_display_name = form_obj.name
        sections, display_names = self._get_sections(form_obj)
        form_section = {}
        section_element_map = {}
        total_forms_ids = {}
        initial_forms_ids = {}
        formset_prefixes = {}
        error_count = 0

        for s in sections:
            logger.debug("handling post data for section %s" % s)
            form_class = create_form_class_for_section(s)
            section_model = Section.objects.get(code=s)
            section_elements = section_model.get_elements()
            section_element_map[s] = section_elements

            logger.debug("created form class for section %s: %s" % (s, form_class))
            logger.debug("POST data = %s" % request.POST)

            if not section_model.allow_multiple:
                form = form_class(request.POST)
                if form.is_valid():
                    logger.debug("form is valid")
                    dynamic_data = form.cleaned_data
                    dyn_patient.save_dynamic_data(registry_code, "cdes", dynamic_data)
                else:
                    for e in form.errors:
                        error_count += 1
                        logger.debug("Validation error on form: %s" % e)

                form_section[s] = form_class(request.POST)

            else:
                if section_model.extra:
                    extra = section_model.extra
                else:
                    extra = 0

                prefix="formset_%s" % s
                formset_prefixes[s] = prefix
                total_forms_ids[s] = "id_%s-TOTAL_FORMS" % prefix
                initial_forms_ids[s] = "id_%s-INITIAL_FORMS" % prefix
                form_set_class = formset_factory(form_class, extra=extra)
                formset  = form_set_class(request.POST,  prefix=prefix)
                assert formset.prefix == prefix

                if formset.is_valid():
                    logger.debug("formset %s is valid" % formset)
                    logger.debug("POST data = %s" % request.POST)
                    dynamic_data = formset.cleaned_data # a list of values
                    section_dict = {}
                    section_dict[s] = dynamic_data
                    dyn_patient.save_dynamic_data(registry_code, "cdes", section_dict)
                    logger.debug("updated data for section %s to %s OK" % (s, dynamic_data) )
                else:
                    for e in formset.errors:
                        error_count += 1
                        logger.debug("Validation error on form: %s" % e)

                form_section[s] = form_set_class(request.POST, prefix=prefix)

        patient_name = '%s %s' % (patient.given_names, patient.family_name)

        context = {
            'registry': registry_code,
            'form_name': form_id,
            'form_display_name': form_display_name,
            'patient_id': patient_id,
            'patient_name': patient_name,
            'sections': sections,
            'forms': form_section,
            'display_names': display_names,
            'section_element_map': section_element_map,
            "total_forms_ids" : total_forms_ids,
            "initial_forms_ids" : initial_forms_ids,
            "formset_prefixes" : formset_prefixes,
        }

        context.update(csrf(request))
        if error_count == 0:
            messages.add_message(request, messages.INFO, 'Patient %s saved successfully' % patient_name)
        else:
            messages.add_message(request, messages.ERROR, 'Patient %s not saved due to validation errors' % patient_name)

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