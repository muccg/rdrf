from django.shortcuts import render_to_response
from django.views.generic.base import View
from django.core.context_processors import csrf
from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages
from django.template import RequestContext
from django.forms.formsets import formset_factory

import logging

from models import RegistryForm, Registry, QuestionnaireResponse
from models import Section
from registry.patients.models import Patient
from dynamic_forms import create_form_class_for_section
from dynamic_data import DynamicDataWrapper
from django.http import Http404
from registration import PatientCreator

logger = logging.getLogger("registry_log")

class FormView(View):

    def __init__(self, *args, **kwargs):
        self.template = 'rdrf_cdes/form.html'
        self.registry = None
        self.dynamic_data = {}
        self.registry_form = None
        self.form_id = None
        self.patient_id = None

        super(FormView, self).__init__(*args, **kwargs)

    def _get_registry(self, registry_code):
        try:
            return Registry.objects.get(code=registry_code)

        except Registry.DoesNotExist:
            raise Http404("Registry %s does not exist" % registry_code)


    def _get_dynamic_data(self, **kwargs):
        if kwargs.has_key('model_class'):
            model_class = kwargs['model_class']
        else:
            model_class = Patient
        obj = model_class.objects.get(pk=kwargs['id'])
        dyn_obj = DynamicDataWrapper(obj)
        dynamic_data = dyn_obj.load_dynamic_data(kwargs['registry_code'],"cdes")
        return dynamic_data

    def get(self, request, registry_code, form_id, patient_id):
        self.form_id = form_id
        self.patient_id = patient_id
        self.registry = self._get_registry(registry_code)
        self.dynamic_data = self._get_dynamic_data(id=patient_id, registry_code=registry_code)
        self.registry_form = self.get_registry_form(form_id)
        context = self._build_context()
        return self._render_context(request, context)

    def _render_context(self, request, context):
        context.update(csrf(request))
        return render_to_response(self.template, context)

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
            messages.add_message(request, messages.SUCCESS, 'Patient %s saved successfully' % patient_name)
        else:
            #class="alert alert-error"
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

    def _get_form_class_for_section(self, section_code):
        return create_form_class_for_section(section_code)

    def _build_context(self):
        sections, display_names = self._get_sections(self.registry_form)
        form_section = {}
        section_element_map = {}
        total_forms_ids = {}
        initial_forms_ids = {}
        formset_prefixes = {}

        for s in sections:
            logger.debug("creating cdes for section %s" % s)
            form_class = self._get_form_class_for_section(s)
            section_model = Section.objects.get(code=s)
            section_elements = section_model.get_elements()
            section_element_map[s] = section_elements

            if not section_model.allow_multiple:
                # return a normal form
                form_section[s] = form_class(self.dynamic_data)
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
                if self.dynamic_data:
                    try:
                        initial_data = self.dynamic_data[s]  # we grab the list of data items by section code not cde code
                        logger.debug("retrieved data for section %s OK" % s)
                    except KeyError, ke:
                        logger.error("patient %s section %s data could not be retrieved: %s" % (self.patient_id, s, ke))
                        initial_data = [""] * len(section_elements)
                else:
                    initial_data = [""] * len(section_elements)

                logger.debug("initial data for section %s = %s" % (s, initial_data))
                form_section[s]  = form_set_class(initial=initial_data, prefix=prefix)


        context = {
            'registry': self.registry.code,
            'form_name': self.form_id,
            'form_display_name': self.registry_form.name,
            'patient_id': self._get_patient_id(),
            'patient_name': self._get_patient_name(),
            'sections': sections,
            'forms': form_section,
            'display_names': display_names,
            'section_element_map': section_element_map,
            "total_forms_ids" : total_forms_ids,
            "initial_forms_ids" : initial_forms_ids,
            "formset_prefixes" : formset_prefixes,
        }

        return context

    def _get_patient_id(self):
        return self.patient_id

    def _get_patient_name(self):
        patient = Patient.objects.get(pk=self.patient_id)
        patient_name = '%s %s' % (patient.given_names, patient.family_name)
        return patient_name


class QuestionnaireView(FormView):
    def __init__(self, *args, **kwargs):
        super(QuestionnaireView, self).__init__(*args, **kwargs)
        self.template = 'rdrf_cdes/questionnaire.html'

    def get(self, request, registry_code):
        self.registry = self._get_registry(registry_code)
        form = self.registry.questionnaire
        if form is None:
            raise Http404("No questionnaire exists for %s" % registry_code)
        else:
            self.registry_form = form
            context = self._build_context()
            return self._render_context(request, context)

    def post(self, request, registry_code):
        error_count  = 0
        registry = self._get_registry(registry_code)
        sections, display_names = self._get_sections(registry.questionnaire)
        data_map = {}           # section --> dynamic data for questionnaire response object if no errors
        form_section = {}       # section --> form instances if there are errors and form needs to be redisplayed
        formset_prefixes = {}
        total_forms_ids = {}
        initial_forms_ids = {}
        section_element_map = {}

        for section in sections:
            section_model = Section.objects.get(code=section)
            section_elements = section_model.get_elements()
            section_element_map[section] = section_elements
            form_class = create_form_class_for_section(section)
            if not section_model.allow_multiple:
                form = form_class(request.POST)
                form_section[section] = form
                if form.is_valid():
                    dynamic_data = form.cleaned_data
                    data_map[section] = dynamic_data
                else:
                    for e in form.errors:
                        error_count += 1
            else:
                if section_model.extra:
                    extra = section_model.extra
                else:
                    extra = 0

                prefix="formset_%s" % section
                form_set_class = formset_factory(form_class, extra=extra)
                form_section[section] = form_set_class(request.POST, prefix=prefix)
                formset_prefixes[section] = prefix
                total_forms_ids[section] = "id_%s-TOTAL_FORMS" % prefix
                initial_forms_ids[section] = "id_%s-INITIAL_FORMS" % prefix
                formset  = form_set_class(request.POST,  prefix=prefix)

                if formset.is_valid():
                    logger.debug("formset %s is valid" % formset)
                    logger.debug("POST data = %s" % request.POST)
                    dynamic_data = formset.cleaned_data # a list of values
                    section_dict = {}
                    section_dict[section] = dynamic_data
                    data_map[section] = section_dict
                else:
                    for e in formset.errors:
                        error_count += 1

        if error_count == 0:
            # persist the data for this response
            questionnaire_response = QuestionnaireResponse()
            questionnaire_response.registry = registry
            questionnaire_response.save()
            questionnaire_response_wrapper = DynamicDataWrapper(questionnaire_response)
            for section in sections:
                questionnaire_response_wrapper.save_dynamic_data(registry_code, "cdes", data_map[section])
            return render_to_response('rdrf_cdes/completed_questionnaire_thankyou.html')
        else:

            context = {
                'registry': registry_code,
                'form_name': 'questionnaire',
                'form_display_name': registry.questionnaire.name,
                'patient_id': 'dummy',
                'patient_name': '',
                'sections': sections,
                'forms': form_section,
                'display_names': display_names,
                'section_element_map': section_element_map,
                "total_forms_ids" : total_forms_ids,
                "initial_forms_ids" : initial_forms_ids,
                "formset_prefixes" : formset_prefixes,
            }

            context.update(csrf(request))
            messages.add_message(request, messages.ERROR, 'The questionnaire was not submitted because of validation errors - please try again')
            return render_to_response('rdrf_cdes/questionnaire.html', context, context_instance=RequestContext(request))

    def _get_patient_id(self):
        return "questionnaire"

    def _get_patient_name(self):
        return "questionnaire"

    def _get_form_class_for_section(self, section_code):
        return create_form_class_for_section(section_code, for_questionnaire=True)


class QuestionnaireResponseView(FormView):

    def __init__(self, *args, **kwargs):
        super(QuestionnaireResponseView, self).__init__(*args, **kwargs)
        self.template = 'rdrf_cdes/approval.html'

    def _get_patient_name(self):
        return "Questionnaire Response for %s" % self.registry.name

    def get(self, request, registry_code, questionnaire_response_id):
        self.patient_id = questionnaire_response_id
        self.registry = self._get_registry(registry_code)
        self.dynamic_data = self._get_dynamic_data(id=questionnaire_response_id, registry_code=registry_code, model_class=QuestionnaireResponse)
        self.registry_form = self.registry.questionnaire
        context = self._build_context()
        context['working_groups'] = self._get_working_groups(request.user)
        return self._render_context(request, context)

    def _get_working_groups(self, auth_user):
        class WorkingGroupOption:
            def __init__(self, working_group_model):
                self.code = working_group_model.pk
                self.desc = working_group_model.name

        from registry.groups.models import User
        user = User.objects.get(user=auth_user)

        return [ WorkingGroupOption(wg) for wg in user.working_groups.all() ]



    def post(self, request, registry_code, questionnaire_response_id):
        self.registry = Registry.objects.get(code=registry_code)
        qr = QuestionnaireResponse.objects.get(pk=questionnaire_response_id)
        if request.POST.has_key('reject'):
            self.template = "rdrf_cdes/rejected.html"
            # delete from Mongo first todo !

            qr.delete()
            logger.debug("deleted rejected questionnaire response %s" % questionnaire_response_id)

        else:
            logger.debug("attempting to create patient from questionnaire response %s" % questionnaire_response_id)
            patient_creator = PatientCreator(self.registry, request.user)
            patient_creator.create_patient(request.POST, qr)
            self.template =  "rdrf_cdes/approved.html"


        context = {}
        context.update(csrf(request))
        return render_to_response(self.template,context)