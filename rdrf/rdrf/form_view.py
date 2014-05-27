from django.shortcuts import render_to_response, RequestContext
from django.views.generic.base import View
from django.core.context_processors import csrf
from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages
from django.template import RequestContext
from django.http import HttpResponse
from django.forms.formsets import formset_factory
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.contrib.auth import get_user_model

import logging

from models import RegistryForm, Registry, QuestionnaireResponse
from models import Section
from registry.patients.models import Patient
from dynamic_forms import create_form_class_for_section
from dynamic_data import DynamicDataWrapper
from django.http import Http404
from registration import PatientCreator, PatientCreatorState
from file_upload import wrap_gridfs_data_for_form

logger = logging.getLogger("registry_log")

def log_context(when, context):
    logger.debug("dumping page context: %s" % when)
    logger.debug("context = %s" % context)
    for section in context["forms"]:
        logger.debug("section %s" % section)
        form = context["forms"][section]
        for attr in form.__dict__:
            value = getattr(form, attr)
            if not callable(value):
                if hasattr(value, "url"):
                    logger.debug("file upload url = %s" % value.url)
                    logger.debug("text value = %s" % value.__unicode__())

                logger.debug("%s form %s = %s" % (section, attr, value))

        for field_name, field_object in form.fields.items():
            field_object = form.fields[field_name]
            for attr in field_object.__dict__:
                logger.debug("field %s.%s = %s" % (field_name, attr, getattr(field_object, attr)))




class FormView(View):

    def __init__(self, *args, **kwargs):
        self.testing = False # when set to True in integration testing, switches off unsupported messaging middleware
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
        if self.testing:
            dyn_obj.testing = True
        dynamic_data = dyn_obj.load_dynamic_data(kwargs['registry_code'],"cdes")
        return dynamic_data

    def get(self, request, registry_code, form_id, patient_id):
        self.form_id = form_id
        self.patient_id = patient_id
        self.registry = self._get_registry(registry_code)
        self.dynamic_data = self._get_dynamic_data(id=patient_id, registry_code=registry_code)
        self.registry_form = self.get_registry_form(form_id)
        context = self._build_context()
        logger.debug("form context = %s" % context)
        return self._render_context(request, context)

    def _render_context(self, request, context):
        context.update(csrf(request))
        return render_to_response(self.template, context, context_instance=RequestContext(request))

    def _get_field_ids(self, form_class):
        # the ids of each cde on the form
        dummy = form_class()
        ids = [ field  for field in dummy.fields.keys() ]
        logger.debug("ids = %s" % ids)
        return ",".join(ids)

    def post(self, request, registry_code, form_id, patient_id):
        patient = Patient.objects.get(pk=patient_id)
        dyn_patient = DynamicDataWrapper(patient)
        if self.testing:
            dyn_patient.testing = True
        form_obj = self.get_registry_form(form_id)
        registry = Registry.objects.get(code=registry_code)
        form_display_name = form_obj.name
        sections, display_names = self._get_sections(form_obj)
        form_section = {}
        section_element_map = {}
        total_forms_ids = {}
        initial_forms_ids = {}
        formset_prefixes = {}
        error_count = 0
        # this is used by formset plugin:
        section_field_ids_map = {} # the full ids on form eg { "section23": ["form23^^sec01^^CDEName", ... ] , ...}

        for section_index, s in enumerate(sections):
            logger.debug("handling post data for section %s" % s)
            section_model = Section.objects.get(code=s)
            form_class = create_form_class_for_section(registry,form_obj, section_model)
            section_elements = section_model.get_elements()
            section_element_map[s] = section_elements
            section_field_ids_map[s] = self._get_field_ids(form_class)

            logger.debug("created form class for section %s: %s" % (s, form_class))
            logger.debug("POST data = %s" % request.POST)
            logger.debug("FILES data = %s" % str(request.FILES))


            if not section_model.allow_multiple:
                form = form_class(request.POST, files=request.FILES)
                if form.is_valid():
                    logger.debug("form is valid")
                    dynamic_data = form.cleaned_data
                    dyn_patient.save_dynamic_data(registry_code, "cdes", dynamic_data)
                    from copy import deepcopy
                    form2 = form_class(dynamic_data,initial=wrap_gridfs_data_for_form(registry_code, deepcopy(dynamic_data)))
                    form_section[s] = form2
                else:
                    for e in form.errors:
                        logger.debug("error validating form: %s" % e)
                        error_count += 1
                        logger.debug("Validation error on form: %s" % e)
                    form_section[s] = form_class(request.POST, request.FILES)

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
                formset  = form_set_class(request.POST, files=request.FILES, prefix=prefix)
                assert formset.prefix == prefix

                if formset.is_valid():
                    logger.debug("formset %s is valid" % formset)
                    logger.debug("POST data = %s" % request.POST)
                    dynamic_data = formset.cleaned_data # a list of values
                    section_dict = {}
                    section_dict[s] = wrap_gridfs_data_for_form(self.registry, dynamic_data)
                    dyn_patient.save_dynamic_data(registry_code, "cdes", section_dict)
                    logger.debug("updated data for section %s to %s OK" % (s, dynamic_data) )
                else:
                    for e in formset.errors:
                        error_count += 1
                        logger.debug("Validation error on form: %s" % e)

                #form_section[s] = form_set_class(request.POST, files=request.FILES, prefix=prefix)

                form_section[s] = form_set_class(initial=wrap_gridfs_data_for_form(registry_code, dynamic_data), prefix=prefix)

        patient_name = '%s %s' % (patient.given_names, patient.family_name)

        context = {
            'registry': registry_code,
            'form_name': form_id,
            'form_display_name': form_display_name,
            'patient_id': patient_id,
            'patient_name': patient_name,
            'sections': sections,
            'section_field_ids_map' : section_field_ids_map,
            'forms': form_section,
            'display_names': display_names,
            'section_element_map': section_element_map,
            "total_forms_ids" : total_forms_ids,
            "initial_forms_ids" : initial_forms_ids,
            "formset_prefixes" : formset_prefixes,
        }

        context.update(csrf(request))
        if error_count == 0:
            if not self.testing:
                messages.add_message(request, messages.SUCCESS, 'Patient %s saved successfully' % patient_name)

        else:
            if not self.testing:
                messages.add_message(request, messages.ERROR, 'Patient %s not saved due to validation errors' % patient_name)

        logger.debug("form context = %s" % context)
        return render_to_response('rdrf_cdes/form.html', context, context_instance=RequestContext(request))


    def _get_sections(self, form):
        section_parts = form.get_sections()
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

    def _get_form_class_for_section(self, registry, registry_form, section):
        return create_form_class_for_section(registry, registry_form, section)

    def _build_context(self):
        sections, display_names = self._get_sections(self.registry_form)
        form_section = {}
        section_element_map = {}
        total_forms_ids = {}
        initial_forms_ids = {}
        formset_prefixes = {}
        section_field_ids_map = {}

        for s in sections:
            logger.debug("creating cdes for section %s" % s)
            section_model = Section.objects.get(code=s)
            form_class = self._get_form_class_for_section(self.registry, self.registry_form,section_model)
            section_elements = section_model.get_elements()
            section_element_map[s] = section_elements
            section_field_ids_map[s] = self._get_field_ids(form_class)
            logger.debug("section field ids map for section %s = %s" % (s,section_field_ids_map[s]))

            if not section_model.allow_multiple:
                # return a normal form

                logger.debug("creating form instance for section %s" % s)
                from copy import deepcopy
                initial_data = wrap_gridfs_data_for_form(self.registry, self.dynamic_data)
                form_section[s] = form_class(self.dynamic_data, initial=initial_data)
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
                        initial_data = wrap_gridfs_data_for_form(self.registry, self.dynamic_data[s])  # we grab the list of data items by section code not cde code
                        logger.debug("retrieved data for section %s OK" % s)
                    except KeyError, ke:
                        logger.error("patient %s section %s data could not be retrieved: %s" % (self.patient_id, s, ke))
                        initial_data = [""] * len(section_elements)
                else:
                    #initial_data = [""] * len(section_elements)
                    initial_data =  [""]  # this appears to forms

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
            'section_field_ids_map' : section_field_ids_map,
            "initial_forms_ids" : initial_forms_ids,
            "formset_prefixes" : formset_prefixes,
        }

        logger.debug("questionnaire context = %s" % context)
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
        try:
            self.registry = self._get_registry(registry_code)
            form = self.registry.questionnaire
            self.registry_form = form
            context = self._build_context()
            return self._render_context(request, context)
        except RegistryForm.DoesNotExist:
            context = {
                'registry': self.registry,
                'error_msg': 'No questionnaire for registry %s' % registry_code
            }
        except RegistryForm.MultipleObjectsReturned:
            context = {
                'registry': self.registry,
                'error_msg': "Multiple questionnaire exists for %s" % registry_code
            }
        return render_to_response('rdrf_cdes/questionnaire_error.html', context)

    def post(self, request, registry_code):
        error_count  = 0
        registry = self._get_registry(registry_code)
        questionnaire_form = RegistryForm.objects.get(registry=registry,is_questionnaire=True)
        sections, display_names = self._get_sections(registry.questionnaire)
        data_map = {}           # section --> dynamic data for questionnaire response object if no errors
        form_section = {}       # section --> form instances if there are errors and form needs to be redisplayed
        formset_prefixes = {}
        total_forms_ids = {}
        initial_forms_ids = {}
        section_element_map = {}
        # this is used by formset plugin:
        section_field_ids_map = {} # the full ids on form eg { "section23": ["form23^^sec01^^CDEName", ... ] , ...}

        for section in sections:
            section_model = Section.objects.get(code=section)
            section_elements = section_model.get_elements()
            section_element_map[section] = section_elements
            form_class = create_form_class_for_section(registry, questionnaire_form, section_model)
            section_field_ids_map[section] = self._get_field_ids(form_class)

            if not section_model.allow_multiple:
                form = form_class(request.POST, request.FILES)
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
                form_section[section] = form_set_class(request.POST,request.FILES, prefix=prefix)
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
            if self.testing:
                questionnaire_response_wrapper.testing = True
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
                'section_field_ids_map' : section_field_ids_map,
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

    def _get_form_class_for_section(self, registry, registry_form, section):
        return create_form_class_for_section(registry, registry_form, section, for_questionnaire=True)


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

        user = get_user_model().objects.get(username=auth_user)

        return [ WorkingGroupOption(wg) for wg in user.working_groups.all() ]

    def post(self, request, registry_code, questionnaire_response_id):
        self.registry = Registry.objects.get(code=registry_code)
        qr = QuestionnaireResponse.objects.get(pk=questionnaire_response_id)
        if request.POST.has_key('reject'):
            # delete from Mongo first todo !
            qr.delete()
            logger.debug("deleted rejected questionnaire response %s" % questionnaire_response_id)
            messages.error(request, "Questionnaire rejected")
        else:
            logger.debug("attempting to create patient from questionnaire response %s" % questionnaire_response_id)
            patient_creator = PatientCreator(self.registry, request.user)
            questionnaire_data = self._get_dynamic_data(id=questionnaire_response_id, registry_code=registry_code, model_class=QuestionnaireResponse)
            patient_creator.create_patient(request.POST, qr, questionnaire_data)
            if patient_creator.state == PatientCreatorState.CREATED_OK:
                messages.info(request, "Questionnaire approved")
            elif patient_creator.state == PatientCreatorState.FAILED_VALIDATION:
                error = patient_creator.error
                messages.error(request, "Patient failed to be created due to validation errors: %s" % error)
            elif patient_creator.state == PatientCreatorState.FAILED:
                error = patient_creator.error
                messages.error(request, "Patient failed to be created: %s" % error)
            else:
                messages.error(request, "Patient failed to be created")

        context = {}
        context.update(csrf(request))
        return HttpResponseRedirect(reverse("admin:rdrf_questionnaireresponse_changelist"))


class FileUploadView(View):
    def get(self, request, registry_code, gridfs_file_id):
        from pymongo import MongoClient
        from bson.objectid import ObjectId
        import gridfs
        client = MongoClient()
        db =client[registry_code]
        fs = gridfs.GridFS(db, collection=registry_code + ".files")
        obj_id = ObjectId(gridfs_file_id)
        data = fs.get(obj_id)
        response = HttpResponse(data , mimetype='application/octet-stream')
        return response

