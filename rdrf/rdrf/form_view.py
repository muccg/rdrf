from django.shortcuts import render_to_response, RequestContext
from django.views.generic.base import View
from django.template.context_processors import csrf
from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.http import HttpResponse
from django.forms.formsets import formset_factory
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.contrib.auth import get_user_model
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from models import RegistryForm, Registry, QuestionnaireResponse
from models import Section, CommonDataElement
from registry.patients.models import Patient, ParentGuardian
from dynamic_forms import create_form_class_for_section
from dynamic_data import DynamicDataWrapper
from django.http import Http404
from registration import PatientCreator, PatientCreatorState
from file_upload import wrap_gridfs_data_for_form
from utils import de_camelcase
from rdrf.utils import location_name, is_multisection, mongo_db_name, make_index_map
from rdrf.mongo_client import construct_mongo_client
from rdrf.wizard import NavigationWizard, NavigationFormType

from rdrf.consent_forms import CustomConsentFormGenerator
from rdrf.utils import get_form_links, consent_status_for_patient

from django.shortcuts import redirect
from django.forms.models import inlineformset_factory
from registry.patients.models import PatientConsent
from registry.patients.admin_forms import PatientConsentFileForm
from operator import itemgetter
import json
import os
from django.conf import settings
from rdrf.actions import ActionExecutor
from rdrf.models import AdjudicationRequest, AdjudicationRequestState, AdjudicationError, AdjudicationDefinition, Adjudication
from rdrf.utils import FormLink
from registry.groups.models import CustomUser
import logging
from registry.groups.models import WorkingGroup
from rdrf.dynamic_forms import create_form_class_for_consent_section

logger = logging.getLogger("registry_log")


class LoginRequiredMixin(object):

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(LoginRequiredMixin, self).dispatch(
            request, *args, **kwargs)


class CustomConsentHelper(object):

    def __init__(self, registry_model):
        self.registry_model = registry_model
        self.custom_consent_errors = {}
        self.custom_consent_data = None
        self.custom_consent_keys = []
        self.custom_consent_wrappers = []
        self.error_count = 0

    def create_custom_consent_wrappers(self):

        for consent_section_model in self.registry_model.consent_sections.order_by("code"):
            consent_form_class = create_form_class_for_consent_section(
                self.registry_model, consent_section_model)
            consent_form = consent_form_class(data=self.custom_consent_data)
            consent_form_wrapper = ConsentFormWrapper(consent_section_model.section_label,
                                                      consent_form,
                                                      consent_section_model)

            self.custom_consent_wrappers.append(consent_form_wrapper)

    def get_custom_consent_keys_from_request(self, request):
        self.custom_consent_data = {}
        for key in request.POST:
            if key.startswith("customconsent_"):
                self.custom_consent_data[key] = request.POST[key]
                self.custom_consent_keys.append(key)

        for key in self.custom_consent_keys:
            del request.POST[key]

    def check_for_errors(self):
        for custom_consent_wrapper in self.custom_consent_wrappers:
            if not custom_consent_wrapper.is_valid():
                self.custom_consent_errors[
                    custom_consent_wrapper.label] = [
                    error_message for error_message in custom_consent_wrapper.errors]
                self.error_count += custom_consent_wrapper.num_errors

    def load_dynamic_data(self, dynamic_data):
        # load data from Mongo
        self.custom_consent_data = dynamic_data.get("custom_consent_data", None)


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
                logger.debug("field %s.%s = %s" %
                             (field_name, attr, getattr(field_object, attr)))


class FormView(View):

    def __init__(self, *args, **kwargs):
        # when set to True in integration testing, switches off unsupported messaging middleware
        self.testing = False
        self.template = None
        self.registry = None
        self.dynamic_data = {}
        self.registry_form = None
        self.form_id = None
        self.patient_id = None
        self.user = None

        super(FormView, self).__init__(*args, **kwargs)

    def _get_registry(self, registry_code):
        try:
            return Registry.objects.get(code=registry_code)

        except Registry.DoesNotExist:
            raise Http404("Registry %s does not exist" % registry_code)

    def _get_dynamic_data(self, **kwargs):
        if 'model_class' in kwargs:
            model_class = kwargs['model_class']
        else:
            model_class = Patient
        obj = model_class.objects.get(pk=kwargs['id'])
        dyn_obj = DynamicDataWrapper(obj)
        if self.testing:
            dyn_obj.testing = True
        dynamic_data = dyn_obj.load_dynamic_data(kwargs['registry_code'], "cdes")
        return dynamic_data

    @method_decorator(login_required)
    def get(self, request, registry_code, form_id, patient_id):
        if request.user.is_working_group_staff:
            raise PermissionDenied()

        self.user = request.user
        self.form_id = form_id
        self.patient_id = patient_id
        self.registry = self._get_registry(registry_code)
        self.dynamic_data = self._get_dynamic_data(id=patient_id, registry_code=registry_code)
        self.registry_form = self.get_registry_form(form_id)
        context = self._build_context(user=request.user)
        context["location"] = location_name(self.registry_form)
        context["header"] = self.registry_form.header
        context["show_print_button"] = True

        patient_model = Patient.objects.get(pk=patient_id)
        wizard = NavigationWizard(self.user,
                                  self.registry,
                                  patient_model,
                                  NavigationFormType.CLINICAL,
                                  self.registry_form)

        context["next_form_link"] = wizard.next_link
        context["previous_form_link"] = wizard.previous_link

        if request.user.is_parent:
            context['parent'] = ParentGuardian.objects.get(user=request.user)

        return self._render_context(request, context)

    def _render_context(self, request, context):
        context.update(csrf(request))
        return render_to_response(
            self._get_template(),
            context,
            context_instance=RequestContext(request))

    def _get_field_ids(self, form_class):
        # the ids of each cde on the form
        dummy = form_class()
        ids = [field for field in dummy.fields.keys()]
        return ",".join(ids)

    @method_decorator(login_required)
    def post(self, request, registry_code, form_id, patient_id):
        if request.user.is_superuser:
            pass
        elif request.user.is_working_group_staff or request.user.has_perm("rdrf.form_%s_is_readonly" % form_id) :
            raise PermissionDenied()

        self.user = request.user
        patient = Patient.objects.get(pk=patient_id)
        self.patient_id = patient_id
        dyn_patient = DynamicDataWrapper(patient)
        if self.testing:
            dyn_patient.testing = True
        form_obj = self.get_registry_form(form_id)
        # this allows form level timestamps to be saved
        dyn_patient.current_form_model = form_obj
        self.registry_form = form_obj
        registry = Registry.objects.get(code=registry_code)
        self.registry = registry
        form_display_name = form_obj.name
        sections, display_names, ids = self._get_sections(form_obj)
        form_section = {}
        section_element_map = {}
        total_forms_ids = {}
        initial_forms_ids = {}
        formset_prefixes = {}
        error_count = 0
        # this is used by formset plugin:
        # the full ids on form eg { "section23": ["form23^^sec01^^CDEName", ... ] , ...}
        section_field_ids_map = {}

        for section_index, s in enumerate(sections):
            section_model = Section.objects.get(code=s)
            form_class = create_form_class_for_section(
                registry,
                form_obj,
                section_model,
                injected_model="Patient",
                injected_model_id=self.patient_id,
                is_superuser=self.request.user.is_superuser,
                patient_model=patient)
            section_elements = section_model.get_elements()
            section_element_map[s] = section_elements
            section_field_ids_map[s] = self._get_field_ids(form_class)

            if not section_model.allow_multiple:
                form = form_class(request.POST, files=request.FILES)
                logger.debug("validating form for section %s" % section_model)
                if form.is_valid():
                    logger.debug("form is valid")
                    dynamic_data = form.cleaned_data
                    dyn_patient.save_dynamic_data(registry_code, "cdes", dynamic_data)

                    from copy import deepcopy
                    form2 = form_class(
                        dynamic_data,
                        initial=wrap_gridfs_data_for_form(
                            registry_code,
                            deepcopy(dynamic_data)))
                    form_section[s] = form2
                else:
                    for e in form.errors:
                        logger.debug("error validating form: %s" % e)
                        error_count += 1
                        logger.debug("Validation error on form: %s" % e)
                    form_section[s] = form_class(request.POST, request.FILES)

            else:
                logger.debug("handling POST of multisection %s" % section_model)
                if section_model.extra:
                    extra = section_model.extra
                else:
                    extra = 0

                prefix = "formset_%s" % s
                formset_prefixes[s] = prefix
                total_forms_ids[s] = "id_%s-TOTAL_FORMS" % prefix
                initial_forms_ids[s] = "id_%s-INITIAL_FORMS" % prefix
                form_set_class = formset_factory(form_class, extra=extra, can_delete=True)
                formset = form_set_class(request.POST, files=request.FILES, prefix=prefix)
                assert formset.prefix == prefix

                if formset.is_valid():
                    dynamic_data = formset.cleaned_data  # a list of values
                    logger.debug("multisection formset is valid")
                    logger.debug("cleaned dynamic_data = %s" % dynamic_data)

                    index_actions = []  # 101010 means the second item was deleted, first wass kept as was third etc
                    to_remove = []

                    for item_index, dd in enumerate(dynamic_data):
                        if 'DELETE' in dd and dd['DELETE']:
                            logger.debug("removed DELETED section item: %s" % dd)
                            #dynamic_data.remove(dd)
                            to_remove.append(dd)
                            index_actions.append(0)
                        else:
                            index_actions.append(1)

                    for dd in to_remove:
                        dynamic_data.remove(dd)

                    index_map = make_index_map(index_actions)

                    logger.debug("dynamic data after deletions: %s" % dynamic_data)

                    section_dict = {}

                    # section_dict[s] = wrap_gridfs_data_for_form
                    #     self.registry.code, dynamic_data)

                    section_dict[s] = dynamic_data

                    #logger.debug("** after wrapping mutlisection for gridfs = %s" % section_dict)

                    dyn_patient.save_dynamic_data(registry_code, "cdes", section_dict, multisection=True,
                                                  index_map=index_map)
                    logger.debug("saved dynamic data to mongo OK")

                    #data_after_save = dyn_patient.load_dynamic_data(self.registry.code, "cdes")
                    wrapped_data_for_form = wrap_gridfs_data_for_form(registry_code, dynamic_data)

                    form_section[s] = form_set_class(initial=wrapped_data_for_form, prefix=prefix)

                else:
                    logger.debug("formset for multisection is invalid!")
                    for e in formset.errors:
                        error_count += 1
                        logger.debug("Validation error on form: %s" % e)
                    form_section[s] = form_set_class(request.POST, request.FILES, prefix=prefix)

        # Save one snapshot after all sections have being persisted
        dyn_patient.save_snapshot(registry_code, "cdes")

        patient_name = '%s %s' % (patient.given_names, patient.family_name)

        wizard = NavigationWizard(self.user,
                                  registry,
                                  patient,
                                  NavigationFormType.CLINICAL,
                                  form_obj)

        context = {
            'current_registry_name': registry.name,
            'current_form_name': de_camelcase(form_obj.name),
            'registry': registry_code,
            'registry_code': registry_code,
            'form_name': form_id,
            'form_display_name': form_display_name,
            'patient_id': patient_id,
            'patient_name': patient_name,
            'sections': sections,
            'section_field_ids_map': section_field_ids_map,
            'section_ids': ids,
            'forms': form_section,
            'display_names': display_names,
            'section_element_map': section_element_map,
            "total_forms_ids": total_forms_ids,
            "initial_forms_ids": initial_forms_ids,
            "formset_prefixes": formset_prefixes,
            "form_links": self._get_formlinks(request.user),
            "metadata_json_for_sections": self._get_metadata_json_dict(self.registry_form),
            "has_form_progress": self.registry_form.has_progress_indicator,
            "location": location_name(self.registry_form),
            "next_form_link": wizard.next_link,
            "previous_form_link": wizard.previous_link,
        }

        if request.user.is_parent:
            context['parent'] = ParentGuardian.objects.get(user=request.user)

        if not self.registry_form.is_questionnaire:
            cdes_status, progress = self._get_patient_object().form_progress(self.registry_form)
            context["form_progress"] = progress
            context["form_progress_cdes"] = cdes_status

        context.update(csrf(request))
        if error_count == 0:
            if not self.testing:
                messages.add_message(
                    request, messages.SUCCESS, 'Patient %s saved successfully' % patient_name)
        else:
            if not self.testing:
                messages.add_message(
                    request,
                    messages.ERROR,
                    'Patient %s not saved due to validation errors' %
                    patient_name)

        return render_to_response(
            self._get_template(),
            context,
            context_instance=RequestContext(request))

    def _get_sections(self, form):
        section_parts = form.get_sections()
        sections = []
        display_names = {}
        ids = {}
        for s in section_parts:
            try:
                sec = Section.objects.get(code=s.strip())
                display_names[s] = sec.display_name
                ids[s] = sec.id
                sections.append(s)
            except ObjectDoesNotExist:
                logger.error("Section %s does not exist" % s)
        return sections, display_names, ids

    def get_registry_form(self, form_id):
        return RegistryForm.objects.get(id=form_id)

    def _get_form_class_for_section(self, registry, registry_form, section):
        return create_form_class_for_section(
            registry,
            registry_form,
            section,
            injected_model="Patient",
            injected_model_id=self.patient_id,
            is_superuser=self.request.user.is_superuser,
            user_groups=self.request.user.groups.all())

    def _get_formlinks(self, user):

        if user is not None:
            return [
                FormLink(
                    self.patient_id,
                    self.registry,
                    form,
                    selected=(
                        form.name == self.registry_form.name)) for form in self.registry.forms if not form.is_questionnaire and user.can_view(form)]
        else:
            return []

    def _build_context(self, **kwargs):
        """
        :param kwargs: extra key value pairs to be passed into the built context
        :return: a context dictionary to render the template ( all form generation done here)
        """
        user = kwargs.get("user", None)

        sections, display_names, ids = self._get_sections(self.registry_form)
        form_section = {}
        section_element_map = {}
        total_forms_ids = {}
        initial_forms_ids = {}
        formset_prefixes = {}
        section_field_ids_map = {}
        form_links = self._get_formlinks(user)
        if self.dynamic_data:
            if 'questionnaire_context' in kwargs:
                self.dynamic_data['questionnaire_context'] = kwargs['questionnaire_context']
            else:
                self.dynamic_data['questionnaire_context'] = 'au'

        for s in sections:
            section_model = Section.objects.get(code=s)
            form_class = self._get_form_class_for_section(
                self.registry, self.registry_form, section_model)
            section_elements = section_model.get_elements()
            section_element_map[s] = section_elements
            section_field_ids_map[s] = self._get_field_ids(form_class)

            if not section_model.allow_multiple:
                # return a normal form
                initial_data = wrap_gridfs_data_for_form(self.registry, self.dynamic_data)
                form_section[s] = form_class(self.dynamic_data, initial=initial_data)

            else:
                # Ensure that we can have multiple formsets on the one page
                prefix = "formset_%s" % s
                formset_prefixes[s] = prefix
                total_forms_ids[s] = "id_%s-TOTAL_FORMS" % prefix
                initial_forms_ids[s] = "id_%s-INITIAL_FORMS" % prefix

                # return a formset
                if section_model.extra:
                    extra = section_model.extra
                else:
                    extra = 0
                form_set_class = formset_factory(form_class, extra=extra, can_delete=True)
                if self.dynamic_data:
                    try:
                        # we grab the list of data items by section code not cde code
                        initial_data = wrap_gridfs_data_for_form(
                            self.registry, self.dynamic_data[s])
                    except KeyError as ke:
                        logger.error(
                            "patient %s section %s data could not be retrieved: %s" %
                            (self.patient_id, s, ke))
                        initial_data = [""]  # * len(section_elements)
                else:
                    # initial_data = [""] * len(section_elements)
                    initial_data = [""]  # this appears to forms

                form_section[s] = form_set_class(initial=initial_data, prefix=prefix)

        context = {
            'old_style_demographics': self.registry.code != 'fkrp',
            'current_registry_name': self.registry.name,
            'current_form_name': de_camelcase(self.registry_form.name),
            'registry': self.registry.code,
            'registry_code': self.registry.code,
            'form_name': self.form_id,
            'form_display_name': self.registry_form.name,
            'patient_id': self._get_patient_id(),
            'patient_name': self._get_patient_name(),
            'sections': sections,
            'forms': form_section,
            'display_names': display_names,
            'section_ids': ids,
            'section_element_map': section_element_map,
            "total_forms_ids": total_forms_ids,
            'section_field_ids_map': section_field_ids_map,
            "initial_forms_ids": initial_forms_ids,
            "formset_prefixes": formset_prefixes,
            "form_links": form_links,
            "metadata_json_for_sections": self._get_metadata_json_dict(self.registry_form),
            "has_form_progress": self.registry_form.has_progress_indicator
        }

        if not self.registry_form.is_questionnaire and self.registry_form.has_progress_indicator:
            cdes_status, progress = self._get_patient_object().form_progress(self.registry_form)
            context["form_progress"] = progress
            context["form_progress_cdes"] = cdes_status

        context.update(kwargs)
        return context

    def _get_patient_id(self):
        return self.patient_id

    def _get_patient_name(self):
        patient = Patient.objects.get(pk=self.patient_id)
        patient_name = '%s %s' % (patient.given_names, patient.family_name)
        return patient_name

    def _get_patient_object(self):
        return Patient.objects.get(pk=self.patient_id)

    def _get_metadata_json_dict(self, registry_form):
        """
        :param registry_form model instance
        :return: a dictionary of section --> metadata json for cdes in the section
        Used by the dynamic formset plugin client side to override behaviour

        We only provide overrides here at the moment
        """
        json_dict = {}
        from utils import id_on_page
        for section in registry_form.get_sections():
            metadata = {}
            section_model = Section.objects.get(code=section)
            for cde_code in section_model.get_elements():
                try:
                    cde = CommonDataElement.objects.get(code=cde_code)
                    cde_code_on_page = id_on_page(registry_form, section_model, cde)
                    if cde.datatype.lower() == "date":
                        # date widgets are complex
                        metadata[cde_code_on_page] = {}
                        metadata[cde_code_on_page]["row_selector"] = cde_code_on_page + "_month"
                except CommonDataElement.DoesNotExist:
                    continue

            if metadata:
                json_dict[section] = json.dumps(metadata)

        return json_dict

    def _get_template(self, ):
        if self.user.has_perm("rdrf.form_%s_is_readonly" % self.form_id) and not self.user.is_superuser:
            return "rdrf_cdes/form_readonly.html"
        return "rdrf_cdes/form.html"


class FormPrintView(FormView):
    
    def _get_template(self):
        return "rdrf_cdes/form_print.html"


class ConsentFormWrapper(object):

    def __init__(self, label, form, consent_section_model):
        self.label = label
        self.form = form
        self.consent_section_model = consent_section_model  # handly

    def is_valid(self):
        return self.form.is_valid()

    @property
    def errors(self):
        messages = []
        for field in self.form.errors:
            for message in self.form.errors[field]:
                logger.debug("consent error for %s: %s" % (self.label, message))
                messages.append("Consent Section Invalid")

        return messages

    @property
    def num_errors(self):
        return len(self.errors)


class ConsentQuestionWrapper(object):

    def __init__(self):
        self.label = ""
        self.answer = "No"


class QuestionnaireView(FormView):

    def __init__(self, *args, **kwargs):
        super(QuestionnaireView, self).__init__(*args, **kwargs)
        self.questionnaire_context = None
        self.template = 'rdrf_cdes/questionnaire.html'

    from patient_decorators import patient_has_access

    @method_decorator(patient_has_access)
    def get(self, request, registry_code, questionnaire_context="au"):
        try:
            if questionnaire_context is not None:
                self.questionnaire_context = questionnaire_context
            else:
                self.questionnaire_context = 'au'
            self.registry = self._get_registry(registry_code)
            form = self.registry.questionnaire
            if form is None:
                raise RegistryForm.DoesNotExist()

            self.registry_form = form
            context = self._build_context(questionnaire_context=questionnaire_context)

            custom_consent_helper = CustomConsentHelper(self.registry)
            custom_consent_helper.create_custom_consent_wrappers()

            context["custom_consent_errors"] = {}
            context["custom_consent_wrappers"] = custom_consent_helper.custom_consent_wrappers
            context["registry"] = self.registry
            context["country_code"] = questionnaire_context
            context["prelude_file"] = self._get_prelude(registry_code, questionnaire_context)
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

    def _get_prelude(self, registry_code, questionnaire_context):
        if questionnaire_context is None:
            prelude_file = "prelude_%s.html" % registry_code
        else:
            prelude_file = "prelude_%s_%s.html" % (registry_code, questionnaire_context)

        file_path = os.path.join(settings.TEMPLATE_DIRS[0], 'rdrf_cdes', prelude_file)
        if os.path.exists(file_path):
            return os.path.join('rdrf_cdes', prelude_file)
        else:
            return None

    def _get_questionnaire_context(self, request):
        parts = request.path.split("/")
        context_flag = parts[-1]
        if context_flag in ["au", "nz"]:
            return context_flag
        else:
            return "au"

    def _create_custom_consents_wrappers(self, post_data=None):
        consent_form_wrappers = []

        for consent_section_model in self.registry.consent_sections.order_by("code"):
            consent_form_class = create_form_class_for_consent_section(
                self.registry, consent_section_model)
            consent_form = consent_form_class(data=post_data)
            consent_form_wrapper = ConsentFormWrapper(
                consent_section_model.section_label, consent_form, consent_section_model)
            consent_form_wrappers.append(consent_form_wrapper)

        return consent_form_wrappers

    @method_decorator(patient_has_access)
    def post(self, request, registry_code, **kwargs):
        error_count = 0
        registry = self._get_registry(registry_code)
        self.registry = registry

        # RDR-871 Allow "custom consents"
        custom_consent_helper = CustomConsentHelper(self.registry)
        custom_consent_helper.get_custom_consent_keys_from_request(request)
        custom_consent_helper.create_custom_consent_wrappers()
        custom_consent_helper.check_for_errors()

        error_count += custom_consent_helper.error_count

        logger.debug("Error count after checking custom consents = %s" % error_count)

        self.questionnaire_context = self._get_questionnaire_context(request)

        questionnaire_form = registry.questionnaire
        self.registry_form = questionnaire_form
        sections, display_names, ids = self._get_sections(registry.questionnaire)
        # section --> dynamic data for questionnaire response object if no errors
        data_map = {}
        # section --> form instances if there are errors and form needs to be redisplayed
        form_section = {}
        formset_prefixes = {}
        total_forms_ids = {}
        initial_forms_ids = {}
        section_element_map = {}
        # this is used by formset plugin:
        # the full ids on form eg { "section23": ["form23^^sec01^^CDEName", ... ] , ...}
        section_field_ids_map = {}

        for section in sections:
            logger.debug("processing section %s" % section)
            section_model = Section.objects.get(code=section)
            section_elements = section_model.get_elements()
            section_element_map[section] = section_elements
            form_class = create_form_class_for_section(
                registry,
                questionnaire_form,
                section_model,
                questionnaire_context=self.questionnaire_context)
            section_field_ids_map[section] = self._get_field_ids(form_class)

            if not section_model.allow_multiple:
                form = form_class(request.POST, request.FILES)
                form_section[section] = form
                if form.is_valid():
                    logger.debug("section %s is valid" % section_model.display_name)
                    dynamic_data = form.cleaned_data
                    data_map[section] = dynamic_data
                else:
                    logger.debug("section %s is NOT valid" % section_model.display_name)
                    for e in form.errors:
                        logger.debug("Error in %s: %s" % (section_model.display_name, e))
                        error_count += 1
            else:
                if section_model.extra:
                    extra = section_model.extra
                else:
                    extra = 0

                prefix = "formset_%s" % section
                form_set_class = formset_factory(form_class, extra=extra, can_delete=True)
                form_section[section] = form_set_class(
                    request.POST, request.FILES, prefix=prefix)
                formset_prefixes[section] = prefix
                total_forms_ids[section] = "id_%s-TOTAL_FORMS" % prefix
                initial_forms_ids[section] = "id_%s-INITIAL_FORMS" % prefix
                formset = form_set_class(request.POST, prefix=prefix)

                if formset.is_valid():
                    logger.debug("section %s is valid" % section_model.display_name)
                    dynamic_data = formset.cleaned_data  # a list of values
                    section_dict = {}
                    section_dict[section] = dynamic_data
                    data_map[section] = section_dict
                else:
                    logger.debug("section %s is NOT valid" % section_model.display_name)
                    for e in formset.errors:
                        logger.debug("Error in %s: %s" % (section_model.display_name, e))
                        error_count += 1

        if error_count == 0:
            logger.debug("All forms are valid")

            questionnaire_response = QuestionnaireResponse()
            questionnaire_response.registry = registry
            questionnaire_response.save()
            questionnaire_response_wrapper = DynamicDataWrapper(questionnaire_response)
            questionnaire_response_wrapper.current_form_model = questionnaire_form
            questionnaire_response_wrapper.save_dynamic_data(
                registry_code, "cdes", {
                    "custom_consent_data": custom_consent_helper.custom_consent_data})

            if self.testing:
                questionnaire_response_wrapper.testing = True
            for section in sections:
                data_map[section]['questionnaire_context'] = self.questionnaire_context
                if is_multisection(section):
                    questionnaire_response_wrapper.save_dynamic_data(
                        registry_code, "cdes", data_map[section], multisection=True)
                else:
                    questionnaire_response_wrapper.save_dynamic_data(
                    registry_code, "cdes", data_map[section])

            def get_completed_questions(
                    questionnaire_form_model,
                    data_map,
                    custom_consent_data,
                    consent_wrappers):
                from django.utils.datastructures import SortedDict
                section_map = SortedDict()

                class SectionWrapper(object):

                    def __init__(self, label):
                        self.label = label
                        self.is_multi = False
                        self.subsections = []
                        self.questions = []

                    def load_consents(self, consent_section_model, custom_consent_data):
                        for consent_question_model in consent_section_model.questions.order_by(
                                "position"):
                            question_wrapper = ConsentQuestionWrapper()
                            question_wrapper.label = consent_question_model.label(
                                on_questionnaire=True)
                            field_key = consent_question_model.field_key
                            try:
                                value = custom_consent_data[field_key]
                                logger.debug("%s = %s" % (field_key, value))
                                if value == "on":
                                    question_wrapper.answer = "Yes"
                            except KeyError:
                                pass
                            self.questions.append(question_wrapper)

                class Question(object):

                    def __init__(self, delimited_key, value):
                        self.delimited_key = delimited_key              # in Mongo
                        self.value = value                              # value in Mongo
                        # label looked up via cde code
                        self.label = self._get_label(delimited_key)
                        # display value if a range
                        self.answer = self._get_answer()
                        self.is_multi = False

                    def _get_label(self, delimited_key):
                        _, _, cde_code = delimited_key.split("____")
                        cde_model = CommonDataElement.objects.get(code=cde_code)
                        return cde_model.name

                    def _get_answer(self):
                        if self.value is None:
                            return " "
                        elif self.value == "":
                            return " "
                        else:
                            cde_model = self._get_cde_model()
                            if cde_model.pv_group:
                                range_dict = cde_model.pv_group.as_dict()
                                for value_dict in range_dict["values"]:
                                    if value_dict["code"] == self.value:
                                        if value_dict["questionnaire_value"]:
                                            return value_dict["questionnaire_value"]
                                        else:
                                            return value_dict["value"]
                            elif cde_model.datatype == 'boolean':
                                if self.value:
                                    return "Yes"
                                else:
                                    return "No"
                            elif cde_model.datatype == 'date':
                                return self.value.strftime("%d-%m-%Y")
                            return str(self.value)

                    def _get_cde_model(self):
                        _, _, cde_code = self.delimited_key.split("____")
                        return CommonDataElement.objects.get(code=cde_code)

                def get_question(form_model, section_model, cde_model, data_map):
                    from rdrf.utils import mongo_key_from_models
                    delimited_key = mongo_key_from_models(form_model, section_model, cde_model)
                    section_data = data_map[section_model.code]
                    if delimited_key in section_data:
                        value = section_data[delimited_key]
                    else:
                        value = None
                    return Question(delimited_key, value)

                # Add custom consents first so they appear on top
                for consent_wrapper in custom_consent_helper.custom_consent_wrappers:
                    sw = SectionWrapper(consent_wrapper.label)
                    consent_section_model = consent_wrapper.consent_section_model
                    sw.load_consents(
                        consent_section_model, custom_consent_helper.custom_consent_data)
                    section_map[sw.label] = sw

                for section_model in questionnaire_form_model.section_models:
                    section_label = section_model.questionnaire_display_name or section_model.display_name
                    if section_label not in section_map:
                        section_map[section_label] = SectionWrapper(section_label)
                    if not section_model.allow_multiple:

                        for cde_model in section_model.cde_models:
                            question = get_question(
                                questionnaire_form_model, section_model, cde_model, data_map)
                            section_map[section_label].questions.append(question)
                    else:
                        section_map[section_label].is_multi = True

                        for multisection_map in data_map[
                                section_model.code][
                                section_model.code]:
                            subsection = []
                            section_wrapper = {section_model.code: multisection_map}
                            for cde_model in section_model.cde_models:
                                question = get_question(
                                    questionnaire_form_model,
                                    section_model,
                                    cde_model,
                                    section_wrapper)
                                subsection.append(question)
                            section_map[section_label].subsections.append(subsection)

                return section_map

            section_map = get_completed_questions(questionnaire_form,
                                                  data_map,
                                                  custom_consent_helper.custom_consent_data,
                                                  custom_consent_helper.custom_consent_wrappers)

            context = {}
            context["custom_consent_errors"] = {}
            context["completed_sections"] = section_map
            context["prelude"] = self._get_prelude(registry_code, self.questionnaire_context)

            return render_to_response(
                'rdrf_cdes/completed_questionnaire_thankyou.html',
                context)
        else:
            logger.debug("Error count non-zero!:  %s" % error_count)

            context = {
                'custom_consent_wrappers': custom_consent_helper.custom_consent_wrappers,
                'custom_consent_errors': custom_consent_helper.custom_consent_errors,
                'registry': registry_code,
                'form_name': 'questionnaire',
                'form_display_name': registry.questionnaire.name,
                'patient_id': 'dummy',
                'patient_name': '',
                'sections': sections,
                'forms': form_section,
                'display_names': display_names,
                'section_element_map': section_element_map,
                'section_field_ids_map': section_field_ids_map,
                "total_forms_ids": total_forms_ids,
                "initial_forms_ids": initial_forms_ids,
                "formset_prefixes": formset_prefixes,
                "metadata_json_for_sections": self._get_metadata_json_dict(self.registry_form)
            }

            context.update(csrf(request))
            messages.add_message(
                request,
                messages.ERROR,
                'The questionnaire was not submitted because of validation errors - please try again')
            return render_to_response(
                'rdrf_cdes/questionnaire.html',
                context,
                context_instance=RequestContext(request))

    def _get_patient_id(self):
        return "questionnaire"

    def _get_patient_name(self):
        return "questionnaire"

    def _get_form_class_for_section(self, registry, registry_form, section):
        return create_form_class_for_section(
            registry, registry_form, section, questionnaire_context=self.questionnaire_context)


class QuestionnaireResponseView(FormView):

    def __init__(self, *args, **kwargs):
        super(QuestionnaireResponseView, self).__init__(*args, **kwargs)
        self.template = 'rdrf_cdes/approval.html'

    def _get_patient_name(self):
        return "Questionnaire Response for %s" % self.registry.name

    @method_decorator(login_required)
    def get(self, request, registry_code, questionnaire_response_id):
        self.patient_id = questionnaire_response_id
        self.registry = self._get_registry(registry_code)
        self.dynamic_data = self._get_dynamic_data(
            id=questionnaire_response_id,
            registry_code=registry_code,
            model_class=QuestionnaireResponse)
        self.registry_form = self.registry.questionnaire
        context = self._build_context(questionnaire_context=self._get_questionnaire_context())
        self._fix_centre_dropdown(context)
        self._fix_state_and_country_dropdowns(context)

        custom_consent_helper = CustomConsentHelper(self.registry)
        custom_consent_helper.load_dynamic_data(self.dynamic_data)
        custom_consent_helper.create_custom_consent_wrappers()

        context["custom_consent_wrappers"] = custom_consent_helper.custom_consent_wrappers
        context["custom_consent_errors"] = {}
        context['working_groups'] = self._get_working_groups(request.user)
        context["on_approval"] = 'yes'
        return self._render_context(request, context)

    def _get_questionnaire_context(self):
        """
        hack to correctly display the Centres dropdown ( which depends on working group for DM1.)
        questionnaire_context is au for all registries but might be nz for dm1
        """
        for k in self.dynamic_data:
            if "questionnaire_context" in k:
                return self.dynamic_data[k]

        logger.debug("questionnaire_context not in dynamic data")
        return 'au'

    def _fix_centre_dropdown(self, context):
        for field_key, field_object in context['forms']['PatientData'].fields.items():
            if 'CDEPatientCentre' in field_key:
                if hasattr(field_object.widget, "_widget_context"):
                    field_object.widget._widget_context[
                        'questionnaire_context'] = self._get_questionnaire_context()

            if 'CDEPatientNextOfKinState' in field_key:
                if hasattr(field_object.widget, "_widget_context"):
                    field_object.widget._widget_context[
                        'questionnaire_context'] = self._get_questionnaire_context()

    def _fix_state_and_country_dropdowns(self, context):
        from django.forms.widgets import TextInput
        for key, field_object in context["forms"]['PatientData'].fields.items():
            if "CDEPatientNextOfKinState" in key:
                field_object.widget = TextInput()

        for address_form in context["forms"]["PatientDataAddressSection"].forms:
            for key, field_object in address_form.fields.items():
                if "State" in key:
                    field_object.widget = TextInput()

    def _get_working_groups(self, auth_user):
        class WorkingGroupOption:

            def __init__(self, working_group_model):
                self.code = working_group_model.pk
                self.desc = working_group_model.name

        user = get_user_model().objects.get(username=auth_user)

        return [WorkingGroupOption(wg) for wg in user.working_groups.all()]

    @method_decorator(login_required)
    def post(self, request, registry_code, questionnaire_response_id):
        self.registry = Registry.objects.get(code=registry_code)
        qr = QuestionnaireResponse.objects.get(pk=questionnaire_response_id)
        if 'reject' in request.POST:
            # delete from Mongo first todo !
            qr.delete()
            logger.debug("deleted rejected questionnaire response %s" %
                         questionnaire_response_id)
            messages.error(request, "Questionnaire rejected")
        else:
            logger.debug(
                "attempting to create patient from questionnaire response %s" %
                questionnaire_response_id)
            patient_creator = PatientCreator(self.registry, request.user)
            questionnaire_data = self._get_dynamic_data(
                id=questionnaire_response_id,
                registry_code=registry_code,
                model_class=QuestionnaireResponse)
            logger.debug("questionnaire data = %s" % questionnaire_data)

            patient_creator.create_patient(request.POST, qr, questionnaire_data)

            if patient_creator.state == PatientCreatorState.CREATED_OK:
                messages.info(
                    request, "Questionnaire approved - A patient record has now been created")
            elif patient_creator.state == PatientCreatorState.FAILED_VALIDATION:
                error = patient_creator.error
                messages.error(
                    request,
                    "Patient failed to be created due to validation errors: %s" %
                    error)
            elif patient_creator.state == PatientCreatorState.FAILED:
                error = patient_creator.error
                messages.error(request, "Patient failed to be created: %s" % error)
            else:
                messages.error(request, "Patient failed to be created")

        context = {}
        context.update(csrf(request))
        return HttpResponseRedirect(reverse("admin:rdrf_questionnaireresponse_changelist"))


class FileUploadView(View):

    @method_decorator(login_required)
    def get(self, request, registry_code, gridfs_file_id):
        from bson.objectid import ObjectId
        import gridfs
        client = construct_mongo_client()
        db = client[mongo_db_name(registry_code)]
        fs = gridfs.GridFS(db, collection=registry_code + ".files")
        obj_id = ObjectId(gridfs_file_id)
        data = fs.get(obj_id)
        filename = data.filename.split("****")[-1]
        response = HttpResponse(data, content_type='application/octet-stream')
        response['Content-disposition'] = "filename=%s" % filename
        return response


class StandardView(object):
    TEMPLATE_DIR = 'rdrf_cdes'
    INFORMATION = "information.html"
    APPLICATION_ERROR = "application_error.html"

    @staticmethod
    def _render(request, view_type, context):
        context.update(csrf(request))
        template = StandardView.TEMPLATE_DIR + "/" + view_type
        return render_to_response(template, context, context_instance=RequestContext(request))

    @staticmethod
    def render_information(request, message):
        context = {"message": message}
        return StandardView._render(request, StandardView.INFORMATION, context)

    @staticmethod
    def render_error(request, error_message):
        context = {"application_error": error_message}
        return StandardView._render(request, StandardView.APPLICATION_ERROR, context)


class QuestionnaireConfigurationView(View):

    """
    Allow an admin to choose which fields to expose in the questionnaire for a given cinical form
    """
    TEMPLATE = "rdrf_cdes/questionnaire_config.html"

    @method_decorator(login_required)
    def get(self, request, form_pk):
        registry_form = RegistryForm.objects.get(pk=form_pk)

        class QuestionWrapper(object):

            def __init__(self, registry_form, section_model, cde_model):
                self.registry_form = registry_form
                self.section_model = section_model
                self.cde_model = cde_model

            @property
            def clinical(self):
                return self.cde_model.name  # The clinical label

            @property
            def questionnaire(self):
                # The text configured at the cde level for the questionnaire
                return self.cde_model.questionnaire_text

            @property
            def section(self):
                return self.section_model.display_name

            @property
            def code(self):
                return self.section_model.code + "." + self.cde_model.code

            @property
            def exposed(self):
                if self.registry_form.on_questionnaire(
                        self.section_model.code,
                        self.cde_model.code):
                    return "checked"
                else:
                    return ""

        sections = []

        class SectionWrapper(object):

            def __init__(self, registry_form, section_model):
                self.registry_form = registry_form
                self.section_model = section_model

            @property
            def questions(self):
                l = []
                for cde_model in self.section_model.cde_models:
                    l.append(QuestionWrapper(self.registry_form, self.section_model, cde_model))
                return l

            @property
            def name(self):
                return self.section_model.display_name

        for section_model in registry_form.section_models:
            sections.append(SectionWrapper(registry_form, section_model))

        context = {"registry_form": registry_form, "sections": sections}
        return self._render_context(request, context)

    def _render_context(self, request, context):
        context.update(csrf(request))
        return render_to_response(
            self.TEMPLATE,
            context,
            context_instance=RequestContext(request))


class RDRFDesignerCDESEndPoint(View):

    def get(self, request):
        cdes = []

        for cde in CommonDataElement.objects.all():
            cde_dict = {}
            cde_dict["code"] = cde.code
            cde_dict["name"] = cde.name
            cde_dict["questionnaire_text"] = cde.questionnaire_text
            cdes.append(cde_dict)

        cdes_as_json = json.dumps(cdes)
        return HttpResponse(cdes_as_json, content_type="application/json")


class RDRFDesigner(View):

    def get(self, request, reg_pk=0):
        context = {"reg_pk": reg_pk}
        context.update(csrf(request))
        return render_to_response('rdrf_cdes/rdrf-designer.html', context)


class RDRFDesignerRegistryStructureEndPoint(View):

    def get(self, request, reg_pk):
        try:
            registry = Registry.objects.get(pk=reg_pk)
            data = registry.structure
        except Registry.DoesNotExist:
            data = {}

        return HttpResponse(json.dumps(data), content_type="application/json")

    def post(self, request, reg_pk):
        import json
        registry_structure_json = request.body
        try:
            registry_structure = json.loads(registry_structure_json)
        except Exception as ex:
            message = {"message": "Error: Could not load registry structure: %s" %
                       ex, "message_type": "error"}
            message_json = json.dumps(message)
            return HttpResponse(message_json, status=400, content_type="application/json")

        try:
            reg_pk = int(reg_pk)
            if reg_pk == 0:
                registry = Registry()
            else:
                registry = Registry.objects.get(pk=reg_pk)

            registry.structure = registry_structure
            registry.save()
            registry.generate_questionnaire()
            reg_pk = registry.pk

            message = {"message": "Saved registry %s OK" %
                       registry, "message_type": "info", "reg_pk": reg_pk}
            message_json = json.dumps(message)
            return HttpResponse(message_json, status=200, content_type="application/json")

        except Exception as ex:
            message = {"message": "Error: Could not save registry: %s" %
                       ex, "message_type": "error"}
            message_json = json.dumps(message)
            return HttpResponse(message_json, status=400, content_type="application/json")


class RPCHandler(View):

    def post(self, request):
        import json
        rpc_command = request.body
        action_dict = json.loads(rpc_command)
        action_executor = ActionExecutor(request, action_dict)
        client_response_dict = action_executor.run()
        client_response_json = json.dumps(client_response_dict)
        return HttpResponse(client_response_json, status=200, content_type="application/json")


class AdjudicationInitiationView(View):

    @method_decorator(login_required)
    def get(self, request, def_id, patient_id):
        try:
            adj_def = AdjudicationDefinition.objects.get(pk=def_id)
        except AdjudicationDefinition.DoesNotExist:
            return StandardView.render_error(request, "Adjudication Definition not found!")

        try:
            patient = Patient.objects.get(pk=patient_id)
        except Patient.DoesNotExist:
            return StandardView.render_error(
                request,
                "Patient with id %s not found!" %
                patient_id)

        context = adj_def.create_adjudication_inititiation_form_context(patient)
        context.update(csrf(request))
        return render_to_response(
            'rdrf_cdes/adjudication_initiation_form.html',
            context,
            context_instance=RequestContext(request))

    @method_decorator(login_required)
    def post(self, request, def_id, patient_id):
        try:
            adj_def = AdjudicationDefinition.objects.get(pk=def_id)
        except AdjudicationDefinition.DoesNotExist:
            return StandardView.render_error(
                request,
                "Adjudication Definition %s not found" %
                def_id)

        try:
            patient = Patient.objects.get(pk=patient_id)
        except Patient.DoesNotExist:
            return StandardView.render_error(
                request,
                "Patient with id %s not found!" %
                patient_id)

        from rdrf.models import AdjudicationState
        adjudication_state = adj_def.get_state(patient)
        if adjudication_state == AdjudicationState.ADJUDICATED:
            return StandardView.render_error(
                request,
                "This patient has already been adjudicated!")
        elif adjudication_state == AdjudicationState.UNADJUDICATED:
            return StandardView.render_error(
                request,
                "This patient has already had an adjudication initiated")
        elif adjudication_state != AdjudicationState.NOT_CREATED:
            return StandardView.render_error(
                request,
                "Unknown adjudication state '%s' - contact admin" %
                adjudication_state)
        else:
            # no requests have been adjudication requests created for this patient
            sent_ok, errors = self._create_adjudication_requests(
                request, adj_def, patient, request.user)
            if errors:
                return StandardView.render_error(
                    request,
                    "Adjudication Requests created OK for users: %s.<p>But the following errors occurred: %s" %
                    (sent_ok,
                     errors))
            else:
                return StandardView.render_information(
                    request,
                    "Adjudication Request Sent Successfully!")

    def _create_adjudication_requests(
            self,
            request,
            adjudication_definition,
            patient,
            requesting_user):
        form_data = request.POST
        errors = []
        request_created_ok = []
        try:
            adjudication = Adjudication.objects.get(
                definition=adjudication_definition,
                patient_id=patient.pk,
                requesting_username=requesting_user.username)
            raise AdjudicationError(
                "Adjudication already created for this patient and definition")

        except Adjudication.DoesNotExist:
            # this is good
            # adjudication object created as bookkeeping object so adjudicator can
            # launch from admin and decide result
            adjudication = Adjudication(
                definition=adjudication_definition,
                patient_id=patient.pk,
                requesting_username=requesting_user.username)

            adjudication.save()

        target_usernames = []
        target_working_group_names = []
        for k in form_data.keys():
            if k.startswith("user_"):
                target_usernames.append(form_data[k])
            elif k.startswith('group_'):
                target_working_group_names.append(form_data[k])

        for target_username in target_usernames:
            try:
                target_user = CustomUser.objects.get(username=target_username)
            except CustomUser.DoesNotExist as ex:
                errors.append("Could not find user for %s: %s" % (target_username, ex))
                continue

            if not target_user:
                errors.append("Could not find user for %s" % target_username)
                continue
            else:
                try:
                    adjudication_definition.create_adjudication_request(
                        request, requesting_user, patient, target_user)
                    request_created_ok.append(target_username)
                except Exception as ex:
                    errors.append(
                        "Could not create adjudication request object for %s: %s" %
                        (target_user, ex))

        for target_working_group_name in target_working_group_names:
            try:
                target_working_group = WorkingGroup.objects.get(name=target_working_group_name)
            except WorkingGroup.DoesNotExist:
                errors.append("There is no working group called %s" % target_working_group_name)
                continue

            for target_user in target_working_group.users:
                try:
                    adjudication_definition.create_adjudication_request(
                        requesting_user, patient, target_user)
                    request_created_ok.append(target_username)
                except Exception as ex:
                    errors.append(
                        "could not create adjudication request for %s in group %s:%s" %
                        (target_user, target_working_group, ex))
                    continue

        return request_created_ok, errors


class AdjudicationRequestView(View):

    @method_decorator(login_required)
    def get(self, request, adjudication_request_id):
        user = request.user
        from rdrf.models import AdjudicationRequest, AdjudicationRequestState
        try:
            adj_req = AdjudicationRequest.objects.get(
                pk=adjudication_request_id,
                username=user.username,
                state=AdjudicationRequestState.REQUESTED)
        except AdjudicationRequest.DoesNotExist:
            msg = "Adjudication request not found or not for current user or has already been actioned"
            return StandardView.render_error(request, msg)

        if adj_req.decided:
            # The adjudicator has already acted on the information from other requests
            # for this patient
            return StandardView.render_information(
                request,
                "An adjudicator has already made a decision regarding this adjudication - it can no longer be voted on")

        adjudication_form, datapoints = adj_req.create_adjudication_form()

        context = {"adjudication_form": adjudication_form,
                   "datapoints": datapoints,
                   "req": adj_req}

        context.update(csrf(request))
        return render_to_response(
            'rdrf_cdes/adjudication_form.html',
            context,
            context_instance=RequestContext(request))

    @method_decorator(login_required)
    def post(self, request, adjudication_request_id):
        arid = request.POST["arid"]
        if arid != adjudication_request_id:
            raise Http404("Incorrect ID")
        else:
            from rdrf.models import AdjudicationRequest, AdjudicationRequestState, AdjudicationError
            try:
                adj_req = AdjudicationRequest.objects.get(
                    pk=arid,
                    state=AdjudicationRequestState.REQUESTED,
                    username=request.user.username)
                try:
                    adj_req.handle_response(request)
                except AdjudicationError as aerr:
                    return StandardView.render_error(request, "Adjudication Error: %s" % aerr)

                return StandardView.render_information(
                    request,
                    "Adjudication Response submitted successfully!")

            except AdjudicationRequest.DoesNotExist:
                msg = "Cannot submit adjudication - adjudication request with id %s not found" %  \
                    adjudication_request_id
                return StandardView.render_error(request, msg)


class Colours(object):
    grey = "#808080"
    blue = "#0000ff"
    green = "#00ff00"
    red = "#f7464a"
    yellow = "#ffff00"


class AdjudicationResultsView(View):

    def get(self, request, adjudication_definition_id, requesting_user_id, patient_id):
        context = {}
        try:
            adj_def = AdjudicationDefinition.objects.get(pk=adjudication_definition_id)
        except AdjudicationDefinition.DoesNotExist:
            return Http404("Adjudication definition not found")

        adjudicating_username = adj_def.adjudicator_username

        if adjudicating_username != request.user.username:
            return StandardView.render_error(
                request,
                "This adjudication result is not adjudicable by you!")

        try:
            from registry.groups.models import CustomUser
            requesting_user = CustomUser.objects.get(pk=requesting_user_id)
        except CustomUser.DoesNotExist:
            return StandardView.render_error(
                request,
                "Could not find requesting user for this adjudication '%s'" %
                requesting_user_id)

        try:
            adjudication = Adjudication.objects.get(
                definition=adj_def,
                patient_id=patient_id,
                requesting_username=requesting_user.username)
        except Adjudication.DoesNotExist:
            msg = "Could not find adjudication for definition %s patient %s requested by %s" % (
                adj_def, patient_id, requesting_user)

            return StandardView.render_error(request, msg)

        stats, adj_responses = self._get_stats_and_responses(
            patient_id, requesting_user.username, adj_def)
        if len(adj_responses) == 0:
            msg = "No one has responded to the adjudication request yet!- stats are %s" % stats
            return StandardView.render_information(request, msg)

        class StatsField(object):
            COLOURS = {
                AdjudicationRequestState.CREATED: Colours.grey,
                AdjudicationRequestState.REQUESTED: Colours.blue,
                AdjudicationRequestState.PROCESSED: Colours.green,
                AdjudicationRequestState.INVALID: Colours.red,
            }
            LABELS = {
                "C": "Created",
                "R": "Requested",
                "P": "Processed",
                "I": "Invalid",
            }

            def __init__(self, data):
                self.data = data

            @property
            def pie_data(self):
                l = []
                for k in self.data:
                    item = {
                        "value": int(self.data[k]),
                        "color": self.COLOURS[k],
                        "highlight": Colours.yellow,
                        "label": self.LABELS[k]
                    }
                    l.append(item)
                return l

        context["stats"] = StatsField(stats)
        context['patient'] = Patient.objects.get(pk=patient_id)

        class AdjudicationField(object):

            """
            Wrapper to hold values submitted so far for one adjudication field
            """

            def _is_numeric(self, values):
                try:
                    map(float, values)
                    return True
                except ValueError:
                    return False

            def __init__(self, cde, results):
                self.cde = cde
                self.results = results

            @property
            def label(self):
                return self.cde.name

            @property
            def avg(self):
                if not self._is_numeric(self.results):
                    return "NA"

                if len(self.results) > 0:
                    return sum(map(float, self.results)) / float(len(self.results))
                else:
                    return "NA"

            @property
            def id(self):
                return "id_adjudication_%s" % self.cde.code

            def _munge_type(self, values):
                if self._is_numeric(values):
                    return map(float, values)
                else:
                    return values

            def _create_histogram(self):
                h = {}
                if self.cde.datatype == "range":
                    discrete_values = sorted(
                        self._munge_type(self.cde.get_range_members(get_code=False)))
                    for value in discrete_values:
                        h[value] = 0

                for r in self.results:
                    if r in h:
                        h[r] += 1
                    else:
                        h[r] = 1
                return h

            @property
            def bar_chart_data(self):
                histogram = self._create_histogram()
                data = {
                    "labels": histogram.keys(),
                    "datasets": [
                        {
                            "label": self.label,
                            "fillColor": "rgba(220,220,220,0.5)",
                            "strokeColor": "rgba(220,220,220,0.8)",
                            "highlightFill": "rgba(220,220,220,0.75)",
                            "highlightStroke": "rgba(220,220,220,1)",
                            "data": histogram.values()
                        }
                    ]
                }
                return data

        fields = []

        for cde_model in adj_def.cde_models:
            results = self._get_results_for_one_cde(adj_responses, cde_model)
            adj_field = AdjudicationField(cde_model, results)
            fields.append(adj_field)

        context['fields'] = fields
        context['decision_form'] = adj_def.create_decision_form()
        context['adjudication'] = adjudication
        context.update(csrf(request))
        return render_to_response('rdrf_cdes/adjudication_results.html', context,
                                  context_instance=RequestContext(request))

    def _get_results_for_one_cde(self, adjudication_responses, cde_model):
        results = []
        for adjudication_response in adjudication_responses:
            value = adjudication_response.get_cde_value(cde_model)
            results.append(value)
        return results

    def _get_stats_and_responses(
            self,
            patient_id,
            requesting_username,
            adjudication_definition):
        """

        :param patient_id: pk of patient
        :param requesting_username: who requested the adj
        :param adjudication_definition: holds what fields are we adjudicating, what categorisation fields we are using
        :return:
        """
        responses = []
        stats = {}
        for adj_req in AdjudicationRequest.objects.filter(
                definition=adjudication_definition,
                patient=patient_id,
                requesting_username=requesting_username):
            if adj_req.state not in stats:
                stats[adj_req.state] = 1
            else:
                stats[adj_req.state] += 1

            adj_resp = adj_req.response
            if adj_resp:
                responses.append(adj_resp)
        return stats, responses

    @method_decorator(login_required)
    def post(self, request, adjudication_definition_id, requesting_user_id, patient_id):
        from rdrf.models import AdjudicationDefinition, AdjudicationState, AdjudicationDecision
        try:
            adj_def = AdjudicationDefinition.objects.get(pk=adjudication_definition_id)
        except AdjudicationDefinition.DoesNotExist:
            msg = "Adjudication Definition with id %s not found" % adjudication_definition_id
            return StandardView.render_error(request, msg)

        if adj_def.adjudicator_username != request.user.username:
            return StandardView.render_error(
                request,
                "You are not authorised to submit an adjudication for this patient")

        patient_id_on_form = request.POST["patient_id"]
        if patient_id_on_form != patient_id:
            return StandardView.render_error(request, "patient incorrect!")

        try:
            requesting_user = CustomUser.objects.get(pk=requesting_user_id)
        except CustomUser.DoesNotExist:
            return StandardView.render_error(request, "requesting user cannot be found")

        try:
            patient = Patient.objects.get(pk=patient_id)
        except Patient.DoesNotExist:
            return StandardView.render_error(request, "Patient does not exist")

        adjudication_state = adj_def.get_state(patient)

        if adjudication_state == AdjudicationState.NOT_CREATED:
            # No requests have been sent out for this definiton
            msg = "No Adjudication requests have come back for this patient - it cannot be decided yet!"
            return StandardView.render_information(request)

        elif adjudication_state == AdjudicationState.ADJUDICATED:
            return StandardView.render_error(
                request,
                "This patient has already been adjudicated!")
        elif adjudication_state != AdjudicationState.UNADJUDICATED:
            return StandardView.render_error(
                request,
                "Unknown adjudication state: %s" %
                adjudication_state)
        else:
            adj_dec = AdjudicationDecision(definition=adj_def, patient=patient_id)
            action_code_value_pairs = self._get_actions_data(adj_def, request.POST)
            adj_dec.actions = action_code_value_pairs
            adj_dec.save()
            # link the adjudication bookkeeping object to this decision
            try:
                adjudication = Adjudication.objects.get(
                    definition=adj_def,
                    patient_id=patient_id,
                    requesting_username=requesting_user.username)
            except Adjudication.DoesNotExist:
                return StandardView.render_error(request, "Adjudication object doesn't exist")

            adjudication.decision = adj_dec
            adjudication.save()
            result = adjudication.perform_actions(request)
            if result.ok:
                return StandardView.render_information(
                    request,
                    "Your adjudication decision has been sent to %s" %
                    adjudication.requesting_username)
            else:
                return StandardView.render_error(
                    request,
                    "Your adjudication decision was not communicated: %s" %
                    result.error_message)

    def _get_actions_data(self, definition, post_data):
        actions = []
        for adjudication_cde_model in definition.action_cde_models:
            for k in post_data:
                logger.debug(k)
                if adjudication_cde_model.code in k:
                    value = post_data[k]
                    actions.append((adjudication_cde_model.code, value))
        return actions


class PatientsListingView(LoginRequiredMixin, View):

    def get(self, request):
        if request.user.is_patient:
            raise PermissionDenied()

        context = {}
        context.update(csrf(request))

        if request.user.is_superuser:
            registries = [registry_model for registry_model in Registry.objects.all()]
        else:
            registries = [registry_model for registry_model in request.user.registry.all()]

        context["registries"] = registries
        context["location"] = "Patient List"
        
        columns = []

        sorted_by_order = sorted(settings.GRID_PATIENT_LISTING, key=itemgetter('order'), reverse=False)
        
        for definition in sorted_by_order:
            if request.user.is_superuser or definition["access"]["default"] or request.user.has_perm(definition["access"]["permission"]):
                columns.append(
                    {
                        "data" : definition["data"],
                        "label" : definition["label"]
                    }
                )

        context["columns"] = columns

        return render_to_response(
            'rdrf_cdes/patients.html',
            context,
            context_instance=RequestContext(request))


class BootGridApi(View):

    def post(self, request):
        # jquery b
        import json
        post_data = request.POST
        # request data  = <QueryDict: {u'current': [u'1'], u'rowCount': [u'10'],
        # u'searchPhrase': [u'']}>

        logger.debug("post data = %s" % post_data)
        search_command = self._get_search_command(post_data)
        command_result = self._run_search_command(search_command)
        rows = [{"id": p.id,
                 "name": p.given_names,
                 "working_groups": "to do",
                 "date_of_birth": p.date_of_birth,
                 "registry": "to do"} for p in Patient.objects.all()]

        command_result = {"current": 1,
                          "rowCount": len(rows),
                          "rows": rows}

        logger.debug("api request data  = %s" % post_data)
        command_result_json = json.dumps(command_result)

        return HttpResponse(command_result_json, content_type="application/json")

    def _get_search_command(self, post_data):
        return None

    def _run_search_command(self, command):
        return {}


class ConstructorFormView(View):

    def get(self, request, form_name):
        return render_to_response('rdrf_cdes/%s.html' % form_name)


class CustomConsentFormView(View):
    def get(self, request, registry_code, patient_id):
        if not request.user.is_authenticated():
            consent_form_url = reverse('consent_form_view', args=[registry_code, patient_id, ])
            login_url = reverse('login')
            return redirect("%s?next=%s" % (login_url, consent_form_url))

        logger.debug("******************** loading consent form *********************")
        patient_model = Patient.objects.get(pk=patient_id)
        registry_model = Registry.objects.get(code=registry_code)
        form_sections = self._get_form_sections(registry_model, patient_model)
        wizard = NavigationWizard(request.user,
                                  registry_model,
                                  patient_model,
                                  NavigationFormType.CONSENTS,
                                  None)

        try:
            parent = ParentGuardian.objects.get(user=request.user)
        except ParentGuardian.DoesNotExist:
            parent = None

        context = {
            "location": "Consents",
            "forms": form_sections,
            "patient": patient_model,
            "patient_id": patient_model.id,
            "registry_code": registry_code,
            "form_links": get_form_links(request.user, patient_model.id, registry_model),
            "next_form_link": wizard.next_link,
            "previous_form_link": wizard.previous_link,
            "parent": parent,
            "consent": consent_status_for_patient(registry_code, patient_model)
        }

        logger.debug("context = %s" % context)

        logger.debug("******************** rendering get *********************")
        return render_to_response("rdrf_cdes/custom_consent_form.html",
                                  context,
                                  context_instance=RequestContext(request))

    def _get_initial_consent_data(self, patient_model):
        # load initial consent data for custom consent form
        if patient_model is None:
            return {}
        initial_data = {}
        data = patient_model.consent_questions_data
        for consent_field_key in data:
            initial_data[consent_field_key] = data[consent_field_key]
            logger.debug("set initial consent data for %s to %s" %
                         (consent_field_key, data[consent_field_key]))
        return initial_data

    def _get_form_sections(self, registry_model, patient_model):
        custom_consent_form_generator = CustomConsentFormGenerator(registry_model, patient_model)
        initial_data = self._get_initial_consent_data(patient_model)
        custom_consent_form = custom_consent_form_generator.create_form(initial_data)

        patient_consent_file_forms = self._get_consent_file_formset(patient_model)

        consent_sections = custom_consent_form.get_consent_sections()

        patient_section_consent_file = ("Upload Consent File", None)

        # form_sections = [
        #     (
        #         custom_consent_form,
        #         consent_sections,
        #     ),
        #     (
        #         patient_consent_file_form,
        #         (patient_section_consent_file,)
        #     )]

        return self._section_structure(custom_consent_form,
                                       consent_sections,
                                       patient_consent_file_forms,
                                       patient_section_consent_file)

        #return form_sections

    def _get_consent_file_formset(self, patient_model):
        patient_consent_file_formset = inlineformset_factory(
            Patient, PatientConsent, form=PatientConsentFileForm, extra=0, can_delete=True, fields="__all__")

        patient_consent_file_forms = patient_consent_file_formset(instance=patient_model,
                                                                  prefix="patient_consent_file")
        return patient_consent_file_forms

    def _section_structure(self,
                           custom_consent_form,
                           consent_sections,
                           patient_consent_file_forms,
                           patient_section_consent_file):
        return [
            (
                custom_consent_form,
                consent_sections,
            ),
            (
                patient_consent_file_forms,
                (patient_section_consent_file,)
            )]

    def _get_success_url(self, registry_model, patient_model):
        return reverse("consent_form_view", args=[registry_model.code, patient_model.pk])


    def post(self, request, registry_code, patient_id):
        logger.debug("******************** post of consents *********************")
        if not request.user.is_authenticated():
            consent_form_url = reverse('consent_form_view', args=[registry_code, patient_id, ])
            login_url = reverse('login')
            return redirect("%s?next=%s" % (login_url, consent_form_url))

        registry_model = Registry.objects.get(code=registry_code)
        patient_model = Patient.objects.get(id=patient_id)
        wizard = NavigationWizard(request.user,
                                  registry_model,
                                  patient_model,
                                  NavigationFormType.CONSENTS,
                                  None)

        patient_consent_file_formset = inlineformset_factory(Patient, PatientConsent,
                                                             form=PatientConsentFileForm,
                                                             fields="__all__")

        logger.debug("patient consent file formset = %s" % patient_consent_file_formset)

        patient_consent_file_forms = patient_consent_file_formset(request.POST,
                                                                  request.FILES,
                                                                  instance=patient_model,
                                                                  prefix="patient_consent_file")
        patient_section_consent_file = ("Upload Consent File", None)

        custom_consent_form_generator = CustomConsentFormGenerator(registry_model, patient_model)
        custom_consent_form = custom_consent_form_generator.create_form(request.POST)
        consent_sections = custom_consent_form.get_consent_sections()

        forms_to_validate = [custom_consent_form, patient_consent_file_forms]

        form_sections = self._section_structure(custom_consent_form,
                                                consent_sections,
                                                patient_consent_file_forms,
                                                patient_section_consent_file)
        valid_forms = []
        error_messages = []

        for form in forms_to_validate:
            if not form.is_valid():
                valid_forms.append(False)
                if isinstance(form.errors, list):
                    for error_dict in form.errors:
                        for field in error_dict:
                            error_messages.append("%s: %s" % (field, error_dict[field]))
                else:
                    for field in form.errors:
                        for error in form.errors[field]:
                            error_messages.append(error)
            else:
                valid_forms.append(True)

        try:
            parent = ParentGuardian.objects.get(user=request.user)
        except ParentGuardian.DoesNotExist:
            parent = None
    
        context = {
            "location": "Consents",
            "patient": patient_model,
            "patient_id": patient_model.id,
            "registry_code": registry_code,
            "form_links": get_form_links(request.user, patient_model.id, registry_model),
            "next_form_link": wizard.next_link,
            "previous_form_link": wizard.previous_link,
            "forms": form_sections,
            "error_messages": [],
            "parent": parent,
            "consent": consent_status_for_patient(registry_code, patient_model)
        }

        if all(valid_forms):
            logger.debug("******************** forms valid :)  *********************")
            logger.debug("******************** saving any consent files *********************")
            things = patient_consent_file_forms.save()
            patient_consent_file_forms.initial = things
            logger.debug("***** ||| things = %s" % things)
            logger.debug("******************** end of consent file save *********************")
            logger.debug("******************** saving custom consent form *********************")
            custom_consent_form.save()
            logger.debug("******************** end of consent save *********************")
            context["message"] = "Consent details saved successfully"
            return HttpResponseRedirect(self._get_success_url(registry_model, patient_model))

        else:
            logger.debug("******************** forms invalid :( *********************")
            context["message"] = "Some forms invalid"
            context["error_messages"] = error_messages
            context["errors"] = True



        return render_to_response("rdrf_cdes/custom_consent_form.html",
                                  context,
                                  context_instance=RequestContext(request))

