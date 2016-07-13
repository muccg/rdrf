from django.shortcuts import render_to_response, RequestContext, get_object_or_404
from django.views.generic.base import View, TemplateView
from django.template.context_processors import csrf
from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.http import HttpResponse, FileResponse
from django.http import HttpResponseRedirect, HttpResponseNotFound
from django.forms.formsets import formset_factory
from django.core.urlresolvers import reverse
from django.contrib.auth import get_user_model
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from models import RegistryForm, Registry, QuestionnaireResponse
from models import Section, CommonDataElement
from registry.patients.models import Patient, ParentGuardian
from dynamic_forms import create_form_class_for_section
from dynamic_data import DynamicDataWrapper
from django.http import Http404
from questionnaires import PatientCreator, PatientCreatorState
from file_upload import wrap_gridfs_data_for_form
from . import filestorage
from utils import de_camelcase
from rdrf.utils import location_name, is_multisection, mongo_db_name, make_index_map
from rdrf.mongo_client import construct_mongo_client
from rdrf.wizard import NavigationWizard, NavigationFormType
from rdrf.models import RDRFContext
from rdrf.context_menu import PatientContextMenu

from rdrf.consent_forms import CustomConsentFormGenerator
from rdrf.utils import get_form_links, consent_status_for_patient
from rdrf.utils import location_name

from rdrf.contexts_api import RDRFContextManager, RDRFContextError

from django.shortcuts import redirect
from django.db.models import Q
from django.forms.models import inlineformset_factory
from registry.patients.models import PatientConsent
from registry.patients.admin_forms import PatientConsentFileForm
from operator import itemgetter
import json
import os
from collections import OrderedDict
from django.conf import settings
from rdrf.actions import ActionExecutor
from rdrf.models import AdjudicationRequest, AdjudicationRequestState, AdjudicationError, AdjudicationDefinition, Adjudication
from rdrf.models import ContextFormGroup
from rdrf.utils import FormLink
from registry.groups.models import CustomUser
import logging
from registry.groups.models import WorkingGroup
from rdrf.dynamic_forms import create_form_class_for_consent_section
from rdrf.form_progress import FormProgress
from django.core.paginator import Paginator, InvalidPage
from django.contrib.contenttypes.models import ContentType

from rdrf.contexts_api import RDRFContextManager, RDRFContextError
from rdrf.form_progress import FormProgress
from rdrf.locators import PatientLocator
from rdrf.components import RDRFContextLauncherComponent


logger = logging.getLogger(__name__)
login_required_method = method_decorator(login_required)


class RDRFContextSwitchError(Exception):
    pass


class LoginRequiredMixin(object):

    @login_required_method
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
        self.rdrf_context = None

        super(FormView, self).__init__(*args, **kwargs)

    def _get_registry(self, registry_code):
        try:
            return Registry.objects.get(code=registry_code)

        except Registry.DoesNotExist:
            raise Http404("Registry %s does not exist" % registry_code)

    def _get_dynamic_data(self, registry_code=None, rdrf_context_id=None,
                          model_class=Patient, id=None):
        obj = model_class.objects.get(pk=id)
        dyn_obj = DynamicDataWrapper(obj, rdrf_context_id=rdrf_context_id)
        if self.testing:
            dyn_obj.testing = True
        dynamic_data = dyn_obj.load_dynamic_data(registry_code, "cdes")
        return dynamic_data

    def set_rdrf_context(self, patient_model, context_id):
        # Ensure we always have a context , otherwise bail
        self.rdrf_context = None
        try:
            if context_id is None:
                if self.registry.has_feature("contexts"):
                    raise RDRFContextError("Registry %s supports contexts but no context id  passed in url" %
                                           self.registry)
                else:
                    self.rdrf_context = self.rdrf_context_manager.get_or_create_default_context(patient_model)
            else:
                    self.rdrf_context = self.rdrf_context_manager.get_context(context_id, patient_model)

            if self.rdrf_context is None:
                raise RDRFContextSwitchError
            else:
                logger.debug("switched context for patient %s to context %s" % (patient_model,
                                                                                self.rdrf_context.id))

        except RDRFContextError, ex:
            logger.error("Error setting rdrf context id %s for patient %s in %s: %s" % (context_id,
                                                                                        patient_model,
                                                                                        self.registry,
                                                                                        ex))

            raise RDRFContextSwitchError

    @login_required_method
    def get(self, request, registry_code, form_id, patient_id, context_id=None):
        if request.user.is_working_group_staff:
            raise PermissionDenied()
        self.user = request.user
        self.form_id = form_id
        self.patient_id = patient_id
        patient_model = Patient.objects.get(pk=patient_id)
        self.registry = self._get_registry(registry_code)

        self.rdrf_context_manager = RDRFContextManager(self.registry)

        try:
            self.set_rdrf_context(patient_model, context_id)
        except RDRFContextSwitchError:
            return HttpResponseRedirect("/")

        # context is not None here - always
        rdrf_context_id = self.rdrf_context.pk
        logger.debug("********** RDRF CONTEXT ID SET TO %s" % rdrf_context_id)

        self.dynamic_data = self._get_dynamic_data(id=patient_id,
                                                   registry_code=registry_code,
                                                   rdrf_context_id=rdrf_context_id)

        self.registry_form = self.get_registry_form(form_id)

        context_launcher = RDRFContextLauncherComponent(request.user,
                                                        self.registry,
                                                        patient_model,
                                                        self.registry_form.name,
                                                        self.rdrf_context)


        context = self._build_context(user=request.user, patient_model=patient_model)
        context["location"] = location_name(self.registry_form, self.rdrf_context)
        context["header"] = self.registry_form.header
        context["show_print_button"] = True

        wizard = NavigationWizard(self.user,
                                  self.registry,
                                  patient_model,
                                  NavigationFormType.CLINICAL,
                                  context_id,
                                  self.registry_form)

        context["next_form_link"] = wizard.next_link
        context["context_id"] = context_id
        context["previous_form_link"] = wizard.previous_link
        context["context_launcher"] = context_launcher.html

        if request.user.is_parent:
            context['parent'] = ParentGuardian.objects.get(user=request.user)

        context["my_contexts_url"] = patient_model.get_contexts_url(self.registry)
        context["context_id"] = rdrf_context_id

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

    @login_required_method
    def post(self, request, registry_code, form_id, patient_id, context_id=None):
        if request.user.is_superuser:
            pass
        elif request.user.is_working_group_staff or request.user.has_perm("rdrf.form_%s_is_readonly" % form_id) :
            raise PermissionDenied()

        self.user = request.user

        registry = Registry.objects.get(code=registry_code)
        self.registry = registry

        patient = Patient.objects.get(pk=patient_id)
        self.patient_id = patient_id

        self.rdrf_context_manager = RDRFContextManager(self.registry)

        try:
            self.set_rdrf_context(patient, context_id)
        except RDRFContextSwitchError:
            return HttpResponseRedirect("/")

        dyn_patient = DynamicDataWrapper(patient, rdrf_context_id=self.rdrf_context.pk)

        if self.testing:
            dyn_patient.testing = True
        form_obj = self.get_registry_form(form_id)
        # this allows form level timestamps to be saved
        dyn_patient.current_form_model = form_obj
        self.registry_form = form_obj

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
                user_groups=self.user.working_groups.all(),
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

                    to_remove = [i for i, d in enumerate(dynamic_data) if d.get('DELETE')]
                    index_map = make_index_map(to_remove, len(dynamic_data))

                    gone = [dynamic_data[i] for i in to_remove]
                    for i in reversed(to_remove):
                        del dynamic_data[i]

                    section_dict = { s: dynamic_data }

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

        # progress saved to progress collection in mongo
        # the data is returned also
        progress_dict = dyn_patient.save_form_progress(registry_code, context_model=self.rdrf_context)

        logger.debug("progress dict = %s" % progress_dict)

        patient_name = '%s %s' % (patient.given_names, patient.family_name)

        logger.debug("rdrf context = %s" % self.rdrf_context)

        wizard = NavigationWizard(self.user,
                                  registry,
                                  patient,
                                  NavigationFormType.CLINICAL,
                                  context_id,
                                  form_obj)

        context_launcher = RDRFContextLauncherComponent(request.user,
                                                        registry,
                                                        patient,
                                                        self.registry_form.name,
                                                        self.rdrf_context)

        context = {
            'current_registry_name': registry.name,
            'current_form_name': de_camelcase(form_obj.name),
            'registry': registry_code,
            'registry_code': registry_code,
            'form_name': form_id,
            'form_display_name': form_display_name,
            'patient_id': patient_id,
            'patient_link': PatientLocator(registry, patient).link,
            'sections': sections,
            'section_field_ids_map': section_field_ids_map,
            'section_ids': ids,
            'forms': form_section,
            'my_contexts_url': patient.get_contexts_url(self.registry),
            'display_names': display_names,
            'section_element_map': section_element_map,
            "total_forms_ids": total_forms_ids,
            "initial_forms_ids": initial_forms_ids,
            "formset_prefixes": formset_prefixes,
            "form_links": self._get_formlinks(request.user, self.rdrf_context),
            "metadata_json_for_sections": self._get_metadata_json_dict(self.registry_form),
            "has_form_progress": self.registry_form.has_progress_indicator,
            "location": location_name(self.registry_form, self.rdrf_context),
            "next_form_link": wizard.next_link,
            "previous_form_link": wizard.previous_link,
            "context_id": context_id,
            "show_print_button": True,
            "context_launcher" : context_launcher.html,
        }

        if request.user.is_parent:
            context['parent'] = ParentGuardian.objects.get(user=request.user)

        if not self.registry_form.is_questionnaire:
            form_progress_map = progress_dict.get(self.registry_form.name + "_form_progress", {})
            if "percentage" in form_progress_map:
                progress_percentage = form_progress_map["percentage"]
            else:
                progress_percentage = 0

            context["form_progress"] = progress_percentage
            initial_completion_cdes = {cde_model.name: False for cde_model in
                                       self.registry_form.complete_form_cdes.all()}
            context["form_progress_cdes"] = progress_dict.get(self.registry_form.name + "_form_cdes_status",
                                                              initial_completion_cdes)

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

    def _get_formlinks(self, user, context_model=None):
        container_model = self.registry
        if context_model is not None:
            if context_model.context_form_group:
                container_model = context_model.context_form_group
        if user is not None:
            return [
                FormLink(
                    self.patient_id,
                    self.registry,
                    form,
                    selected=(
                        form.name == self.registry_form.name),
                    context_model=self.rdrf_context
                    ) for form in container_model.forms if not form.is_questionnaire and user.can_view(form)]
        else:
            return []

    def _build_context(self, **kwargs):
        """
        :param kwargs: extra key value pairs to be passed into the built context
        :return: a context dictionary to render the template ( all form generation done here)
        """
        user = kwargs.get("user", None)
        patient_model = kwargs.get("patient_model", None)
        sections, display_names, ids = self._get_sections(self.registry_form)
        form_section = {}
        section_element_map = {}
        total_forms_ids = {}
        initial_forms_ids = {}
        formset_prefixes = {}
        section_field_ids_map = {}
        form_links = self._get_formlinks(user, self.rdrf_context)
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
            'patient_link': PatientLocator(self.registry, patient_model).link,
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


            form_progress = FormProgress(self.registry_form.registry)

            form_progress_percentage = form_progress.get_form_progress(self.registry_form,
                                                                       patient_model,
                                                                       self.rdrf_context)

            form_cdes_status = form_progress.get_form_cdes_status(self.registry_form,
                                                                  patient_model,
                                                                  self.rdrf_context)

            #cdes_status, progress = self._get_patient_object().form_progress(self.registry_form)
            context["form_progress"] = form_progress_percentage
            context["form_progress_cdes"] = form_cdes_status

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
            section_model = Section.objects.filter(code=section).first()
            if section_model:
                for cde_code in section_model.get_elements():
                    cde = CommonDataElement.objects.filter(code=cde_code).first()
                    if cde:
                        cde_code_on_page = id_on_page(registry_form, section_model, cde)
                        if cde.datatype.lower() == "date":
                            # date widgets are complex
                            metadata[cde_code_on_page] = {}
                            metadata[cde_code_on_page]["row_selector"] = cde_code_on_page + "_month"

            if metadata:
                json_dict[section] = json.dumps(metadata)

        return json_dict


    # fixme: could replace with TemplateView.get_template_names()
    def _get_template(self):
        if self.user and self.user.has_perm("rdrf.form_%s_is_readonly" % self.form_id) and not self.user.is_superuser:
            return "rdrf_cdes/form_readonly.html"

        return "rdrf_cdes/form.html"


class FormPrintView(FormView):

    def _get_template(self):
        return "rdrf_cdes/form_print.html"

class FormFieldHistoryView(TemplateView):
    template_name = "rdrf_cdes/form_field_history.html"

    @login_required_method
    def get(self, request, **kwargs):
        if request.user.is_working_group_staff:
            raise PermissionDenied()
        return super(FormFieldHistoryView, self).get(request, **kwargs)

    def get_context_data(self, registry_code, form_id, patient_id, context_id, section_code, cde_code):
        context = super(FormFieldHistoryView, self).get_context_data()

        # find database objects from url route params
        reg = get_object_or_404(Registry, code=registry_code)
        reg_form = get_object_or_404(RegistryForm, registry=reg, pk=form_id)
        section = get_object_or_404(Section, code=section_code)
        cde = get_object_or_404(CommonDataElement, code=cde_code)
        patient = get_object_or_404(Patient, pk=patient_id)
        rdrf_context = get_object_or_404(RDRFContext, registry=reg, pk=context_id)

        # grab snapshot values out of mongo documents
        dyn_patient = DynamicDataWrapper(patient, rdrf_context_id=rdrf_context.id)
        val = dyn_patient.get_cde_val(registry_code, reg_form.name,
                                      section_code, cde_code)
        history = dyn_patient.get_cde_history(registry_code, reg_form.name,
                                              section_code, cde_code)

        context.update({
            "cde": cde,
            "value": val,
            "history": history,
        })
        return context


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
            context["show_print_button"] = False

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

    def _get_template(self):
        return "rdrf_cdes/questionnaire.html"

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
                section_map = OrderedDict()

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


class QuestionnaireHandlingView(View):
    @method_decorator(login_required)
    def get(self, request, registry_code, questionnaire_response_id):
        from rdrf.questionnaires import Questionnaire
        context = {}
        template_name = "rdrf_cdes/questionnaire_handling.html"
        context["registry_model"] = Registry.objects.get(code=registry_code)
        context["form_model"]  = context["registry_model"].questionnaire
        context["qr_model"] = QuestionnaireResponse.objects.get(id=questionnaire_response_id)
        context["patient_lookup_url"] = reverse("patient_lookup", args=(registry_code,))

        context["questionnaire"] = Questionnaire(context["registry_model"],
                                                 context["qr_model"])


        context.update(csrf(request))

        return render_to_response(
            template_name,
            context,
            context_instance=RequestContext(request))





    def post(self, request, registry_code, questionnaire_response_id):
        registry_model = Registry.objects.get(code=registry_code)
        existing_patient_id = request.POST.get("existing_patient_id", None)
        qr_model = QuestionnaireResponse.objects.get(id=questionnaire_response_id)
        form_data = request.POST.get("form_data")

        if existing_patient_id is None:
            self._create_patient(registry_model,
                                 qr_model,
                                 form_data)
        else:
           patient_model = Patient.objects.get(pk=existing_patient_id)
           self._update_existing_patient(patient_model,
                                         registry_model,
                                         qr_model,
                                         form_data)

    def _create_patient(self, registry_model, qr_model, form_data):
        pass

    def _update_existing_patient(self,
                                 patient_model,
                                 registry_model,
                                 qr_model,
                                 form_data):
        pass







class QuestionnaireResponseView(FormView):
    """
    DEAD!
    """

    def __init__(self, *args, **kwargs):
        super(QuestionnaireResponseView, self).__init__(*args, **kwargs)
        self.template = 'rdrf_cdes/approval.html'

    def _get_patient_name(self):
        return "Questionnaire Response for %s" % self.registry.name



    @method_decorator(login_required)
    def get(self, request, registry_code, questionnaire_response_id):
        from rdrf.questionnaires import Questionnaire
        self.patient_id = questionnaire_response_id
        self.registry = self._get_registry(registry_code)
        self.dynamic_data = self._get_dynamic_data(
            id=questionnaire_response_id,
            registry_code=registry_code,
            model_class=QuestionnaireResponse)

        questionnaire_response_model = QuestionnaireResponse.objects.get(pk=questionnaire_response_id)

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
        context["show_print_button"] = False

        context["questionnaire"] = Questionnaire(self.registry,
                                                 questionnaire_response_model)

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

    @login_required_method
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

    @login_required_method
    def get(self, request, registry_code, file_id):
        import gridfs
        client = construct_mongo_client()
        db = client[mongo_db_name(registry_code)]
        fs = gridfs.GridFS(db, collection=registry_code + ".files")
        data, filename = filestorage.get_file(file_id, fs)
        if data is not None:
            response = FileResponse(data, content_type='application/octet-stream')
            response['Content-disposition'] = "filename=%s" % filename
        else:
            response = HttpResponseNotFound()
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

    @login_required_method
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

    @login_required_method
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

    @login_required_method
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

    @login_required_method
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

    @login_required_method
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

    @login_required_method
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


class GridColumnsViewer(object):
    def get_columns(self, user):
        columns = []
        sorted_by_order = sorted(self.get_grid_definitions(), key=itemgetter('order'), reverse=False)

        for definition in sorted_by_order:
            if user.is_superuser or definition["access"]["default"] or user.has_perm(definition["access"]["permission"]):
                columns.append(
                    {
                        "data": definition["data"],
                        "label": definition["label"]
                    }
                )

        return columns

    def get_grid_definitions(self):
        return settings.GRID_PATIENT_LISTING


def dump(request):
    for k in sorted(request.GET):
        logger.debug("GET %s = %s" % (k, request.GET[k]))

    for k in sorted(request.POST):
        logger.debug("POST %s = %s" % (k, request.POST[k]))




class DataTableServerSideApi(LoginRequiredMixin, View, GridColumnsViewer):
    MODEL = Patient

    def _get_results(self, request):
        self.custom_ordering = None
        self.user = request.user
        # see http://datatables.net/manual/server-side
        try:
            self.registry_code = request.GET.get("registry_code", None)
            logger.info("got registry code OK = %s" % self.registry_code)
        except Exception, ex:
            logger.error("could not get registry_code from request GET: %s" % ex)

        # can restrict on a particular patient for contexts - NOT usually set
        self.patient_id = request.GET.get("patient_id", None)
        self.context_form_group_id = request.GET.get("context_form_group_id", None)
        if self.context_form_group_id:
            self.context_form_group_model = ContextFormGroup.objects.get(pk=int(self.context_form_group_id))
        else:
            self.context_form_group_model = None

        if self.registry_code is None:
            return []
        try:
            self.registry_model = Registry.objects.get(code=self.registry_code)
            self.supports_contexts = self.registry_model.has_feature("contexts")
            self.rdrf_context_manager = RDRFContextManager(self.registry_model)
        except Registry.DoesNotExist:
            logger.error("patients listing api registry code %s does not exist" % self.registry_code)
            return []

        if not self.user.is_superuser:
            if not self.registry_model.code in [r.code for r in self.user.registry.all()]:
                logger.debug("user isn't in registry!")
                return []

        self.form_progress = FormProgress(self.registry_model)

        search_term = request.POST.get("search[value]", "")
        logger.debug("search term = %s" % search_term)

        draw = int(request.POST.get("draw", None))
        logger.debug("draw = %s" % draw)

        start = int(request.POST.get("start", None))
        logger.debug("start = %s" % start)

        length = int(request.POST.get("length", None))
        logger.debug("length = %s" % length)

        page_number = (start / length) + 1
        logger.debug("page = %s" % page_number)

        sort_field, sort_direction = self._get_ordering(request)

        context = {}
        context.update(csrf(request))
        columns = self.get_columns(self.user)

        queryset = self._get_initial_queryset(self.user, self.registry_code, sort_field, sort_direction)
        record_total = queryset.count()
        logger.debug("record_total = %s" % record_total)

        if search_term:
            filtered_queryset = self._apply_filter(queryset, search_term)
        else:
            filtered_queryset = queryset

        filtered_total = filtered_queryset.count()
        logger.debug("filtered_total = %s" % filtered_total)

        rows = self._run_query(filtered_queryset, length, page_number, columns)

        results_dict = self._get_results_dict(draw, page_number, record_total, filtered_total, rows)
        return results_dict

    def post(self, request):
        results_dict = self._get_results(request)
        json_packet = self._json(results_dict)
        return json_packet

    def _get_ordering(self, request):
        #columns[0][data]:full_name
        #...
        #order[0][column]:1
        #order[0][dir]:asc
        sort_column_index = None
        sort_direction = None
        for key in request.POST:
            if key.startswith("order"):
                if "[column]" in key:
                    sort_column_index = request.POST[key]
                elif "[dir]" in key:
                    sort_direction = request.POST[key]

        column_name = "columns[%s][data]" % sort_column_index
        sort_field = request.POST.get(column_name, None)
        if sort_field == "full_name":
            sort_field = "family_name"

        return sort_field, sort_direction

    def apply_custom_ordering(self, rows):
        return rows

    def _apply_filter(self, queryset, search_phrase):
        queryset = queryset.filter(Q(given_names__icontains=search_phrase) |
                                     Q(family_name__icontains=search_phrase))
        return queryset

    def _run_query(self, query_set, records_per_page, page_number, columns):
        # return objects in requested page
        if self.custom_ordering:
            # we have to retrieve all rows - otehrwise , queryset has already been
            # ordered on base model
            query_set = [r for r in query_set]
            query_set = self.apply_custom_ordering(query_set)

        rows = []
        paginator = Paginator(query_set, records_per_page)
        try:
            page = paginator.page(page_number)
        except InvalidPage:
            logger.error("invalid page number: %s" % page_number)
            return []

        func_map = self._get_func_map(columns)
        self.append_rows(page, rows, func_map)

        return rows

    def append_rows(self, page_object, row_list_to_update, func_map):
        for obj in page_object.object_list:
            row_list_to_update.append(self._get_row_dict(obj, func_map))

    def _get_row_dict(self, instance, func_map):
        # we need to do this so that the progress data for this instance loaded!
        self.form_progress.reset()
        row_dict = {}
        for field in func_map:
            try:
                value = func_map[field](instance)
            except KeyError:
                value = "UNKNOWN COLUMN"
            row_dict[field] = value

        return row_dict

    def _get_func_map(self, columns):
        # we do this once
        from registry.patients.models import Patient
        patient_field_names = [field_object.name for field_object in Patient._meta.fields]
        logger.debug("patient fields = %s" % patient_field_names)

        def patient_func(field):
            def f(patient):
                try:
                    return str(getattr(patient, field))
                except Exception, ex:
                    msg = "Error retrieving grid field %s for patient %s: %s" % (field, patient, ex)
                    logger.error(msg)
                    return "GRID ERROR"

            return f

        def grid_func(obj, field):
            method = getattr(obj, field)

            def f(patient):
                try:
                    return method(patient)
                except Exception, ex:
                    msg = "Error retrieving grid field %s for patient %s: %s" % (field, patient, ex)
                    logger.error(msg)
                    return "GRID ERROR"

            return f

        def k(msg):
            # constant combinator
            def f(patient):
                return msg
            return f

        func_map = {}
        for column in columns:
            field = column["data"]
            logger.debug("checking field %s" % field)
            func_name = "_get_grid_field_%s" % field
            logger.debug("checking %s" % func_name)
            if hasattr(self, func_name):
                    func_map[field] = grid_func(self, func_name)
                    logger.debug("field %s is a serverside api func" % field)
            elif field in patient_field_names:
                logger.debug("field is a patient field")
                func_map[field] = patient_func(field)
                logger.debug("field %s is a patient function" % field)
            else:
                logger.debug("field %s is unknown" % field)
                func_map[field] = k("UNKNOWN COLUMN!")

        return func_map

    def _get_grid_field_diagnosis_progress(self, patient_model):
        if not self.supports_contexts:
            progress_number = self.form_progress.get_group_progress("diagnosis", patient_model)
            template = "<div class='progress'><div class='progress-bar progress-bar-custom' role='progressbar'" + \
                       " aria-valuenow='%s' aria-valuemin='0' aria-valuemax='100' style='width: %s%%'>" + \
                       "<span class='progress-label'>%s%%</span></div></div>"
            return template % (progress_number, progress_number,progress_number)
        else:
            # if registry supports contexts, should use the context browser
            return "N/A"

    def _get_grid_field_data_modules(self, patient_model):
        if not self.supports_contexts:
            default_context_model = self.rdrf_context_manager.get_or_create_default_context(patient_model)
            return self.form_progress.get_data_modules(self.user, patient_model, default_context_model)
        else:
            return "N/A"

    def _get_grid_field_genetic_data_map(self, patient_model):
        if not self.supports_contexts:
            has_genetic_data = self.form_progress.get_group_has_data("genetic", patient_model)
            icon = "ok" if has_genetic_data else "remove"
            color = "green" if has_genetic_data else "red"
            return "<span class='glyphicon glyphicon-%s' style='color:%s'></span>" % (icon, color)
        else:
            return "N/A"

    def _get_grid_field_diagnosis_currency(self, patient_model):
        if not self.supports_contexts:
            diagnosis_currency = self.form_progress.get_group_currency("diagnosis", patient_model)
            icon = "ok" if diagnosis_currency else "remove"
            color = "green" if diagnosis_currency else "red"
            return "<span class='glyphicon glyphicon-%s' style='color:%s'></span>" % (icon, color)
        else:
            return "N/A"

    def _get_grid_field_full_name(self, patient_model):
        if not self.supports_contexts:
            context_model = self.rdrf_context_manager.get_or_create_default_context(patient_model)
        else:
            # get first ?
            patient_content_type = ContentType.objects.get(model='patient')
            contexts = [c for c in RDRFContext.objects.filter(registry=self.registry_model,
                                                              content_type=patient_content_type,
                                                              object_id=patient_model.pk).order_by("id")]

            if len(contexts) > 0:
                context_model = contexts[0]
            else:
                return "NO CONTEXT"

        return "<a href='%s'>%s</a>" % (reverse("patient_edit", kwargs={"registry_code": self.registry_code,
                                                                        "patient_id": patient_model.id,
                                                                        "context_id": context_model.pk}),
                                        patient_model.display_name)

    def _get_grid_field_working_groups_display(self, patient_model):
        return patient_model.working_groups_display

    def _json(self, data):
        json_data = json.dumps(data)
        return HttpResponse(json_data, content_type="application/json")


    def _no_results(self, draw):
        return {
            "draw": draw,
            "recordsTotal": 0,
            "recordsFiltered": 0,
            "rows": []
        }

    def _get_results_dict(self, draw, page, total_records, total_filtered_records, rows):

        #       {
        # "draw": 2,  <-- must be returned , is a counter used by DataTable
        # "recordsTotal": 57,
        # "recordsFiltered": 57,
        # "rows": [
        #   {
        #     "first_name": "Charde",
        #     "last_name": "Marshall",
        #     "position": "Regional Director",
        #     "office": "San Francisco",
        #     "start_date": "16th Oct 08",
        #     "salary": "$470,600"
        #   },..]

        results = {
            "draw": draw,
            "recordsTotal": total_records,
            "recordsFiltered": total_filtered_records,
            "rows": [row for row in rows]
        }

        return results

    def _get_initial_queryset(self, user, registry_code, sort_field, sort_direction):
        registry_queryset = Registry.objects.filter(code=registry_code)
        clinicians_have_patients = Registry.objects.get(code=registry_code).has_feature("clinicians_have_patients")

        if self.patient_id is None:
            # Usual case
            models = self.MODEL.objects.all()
        else:
            models = self.get_restricted_queryset(self.patient_id)

        if not user.is_superuser:
            if user.is_curator:
                query_patients = Q(rdrf_registry__in=registry_queryset) & Q(
                    working_groups__in=user.working_groups.all())
                models = models.filter(query_patients)
            elif user.is_genetic_staff:
                models = models.filter(working_groups__in=user.working_groups.all())
            elif user.is_genetic_curator:
                models = models.filter(working_groups__in=user.working_groups.all())
            elif user.is_working_group_staff:
                models = models.filter(working_groups__in=user.working_groups.all())
            elif user.is_clinician and clinicians_have_patients:
                models = models.filter(clinician=user)
            elif user.is_clinician and not clinicians_have_patients:
                query_patients = Q(rdrf_registry__in=registry_queryset) & Q(
                    working_groups__in=user.working_groups.all())
                models = models.filter(query_patients)
            elif user.is_patient:
                models = models.filter(user=user)
            else:
                models = models.none()
        else:
            models = models.filter(rdrf_registry__in=registry_queryset)

        if all([sort_field, sort_direction]):
            logger.debug("*** ordering %s %s" % (sort_field, sort_direction))

            if sort_direction == "desc":
                sort_field = "-" + sort_field

            models = models.order_by(sort_field)
            logger.debug("sort field = %s" % sort_field)

        logger.debug("found %s patients for initial query" % models.count())
        return models

    def _get_grid_data(self, columns):

        return []

    def get_restricted_queryset(self, patient_id):
        return self.MODEL.objects.filter(pk=patient_id)


class ContextDataTableServerSideApi(DataTableServerSideApi):
    MODEL = RDRFContext

    def apply_custom_ordering(self, rows):
        # we sometimes have to do none Django ( db level ) ordering
        # on fields which are on the related (generic relation) patient model or not stored in django at all
        # keys ['diagnosis_progress', 'display_name', 'context_menu', 'created_at', 'genetic_data_map',
        # 'working_groups_display', 'diagnosis_currency', 'patient_link', 'date_of_birth']

        key_func = None
        if self.custom_ordering.startswith("-"):
            ordering = self.custom_ordering[1:]
            direction = "desc"
        else:
            ordering = self.custom_ordering
            direction = "asc"

        if ordering == "patient_link":
            def get_name(context_model):
                return context_model.content_object.display_name

            key_func = get_name
            logger.debug("key_func is by patient_link")

        elif ordering == "date_of_birth":
            def get_dob(context_model):
                return context_model.content_object.date_of_birth
            key_func = get_dob

        elif ordering == "working_groups_display":
            def get_wg(context_model):
                try:
                    wg = context_model.content_object.working_groups.get()
                    return wg.name
                except Exception,ex:
                    logger.debug("error wg %s" % ex)
                    return ""
            key_func = get_wg

        elif ordering == "diagnosis_progress":
            #get_group_progress(self, group_name, patient_model, context_model=None):
            self.form_progress.reset()

            def get_dp(context_model):
                patient_model = context_model.content_object
                try:
                    return self.form_progress.get_group_progress("diagnosis", patient_model, context_model)
                except:
                    return 0

            key_func = get_dp

        elif ordering == "diagnosis_currency":
            self.form_progress.reset()

            def get_dc(context_model):
                patient_model = context_model.content_object
                try:
                    return self.form_progress.get_group_currency("diagnosis", patient_model, context_model)
                except:
                    return False

            key_func = get_dc

        elif ordering == "genetic_data_map":
            self.form_progress.reset()

            def get_gendatamap(context_model):
                patient_model = context_model.content_object
                try:
                    return self.form_progress.get_group_has_data("genetic", patient_model, context_model)
                except:
                    return False

            key_func = get_gendatamap


        if key_func is None:
            logger.debug("key_func is none - not sorting")
            return rows

        d = direction == "desc"

        return sorted(rows, key=key_func, reverse=d)

    def get_grid_definitions(self):
        return settings.GRID_CONTEXT_LISTING

    def _get_initial_queryset(self, user, registry_code, sort_field, sort_direction):

        content_type = ContentType.objects.get(model='patient')

        if self.patient_id is None:
            contexts = RDRFContext.objects.filter(registry=self.registry_model, content_type=content_type)
        else:
            contexts = RDRFContext.objects.filter(registry=self.registry_model,
                                                 content_type=content_type,
                                                 object_id=self.patient_id)

        if self.context_form_group_model is not None:
            contexts = contexts.filter(context_form_group=self.context_form_group_model)

        registry_queryset = Registry.objects.filter(code=registry_code)

        clinicians_have_patients = Registry.objects.get(code=registry_code).has_feature("clinicians_have_patients")

        if not user.is_superuser:
            if user.is_curator:
                query_patients = Q(rdrf_registry__in=registry_queryset) & Q(working_groups__in=user.working_groups.all())
            elif user.is_genetic_staff:
                query_patients = Q(working_groups__in=user.working_groups.all())
            elif user.is_genetic_curator:
                query_patients = Q(working_groups__in=user.working_groups.all())
            elif user.is_working_group_staff:
                query_patients = Q(working_groups__in=user.working_groups.all())
            elif user.is_clinician and clinicians_have_patients:
                query_patients = Q(clinician=user)
            elif user.is_clinician and not clinicians_have_patients:
                query_patients = Q(rdrf_registry__in=registry_queryset) & Q(
                    working_groups__in=user.working_groups.all())
            elif user.is_patient:
                query_patients = Q(user=user)
            else:
                query_patients = Patient.objects.none()
        else:
            query_patients = Q(rdrf_registry__in=registry_queryset)

        patients = Patient.objects.filter(query_patients)
        contexts = contexts.filter(object_id__in=[p.pk for p in patients])

        if all([sort_field, sort_direction]):

            # context model fields
            #content_object, content_type, content_type_id, created_at, display_name, id,
            # last_updated, object_id, registry, registry_id

            if sort_field in ['display_name', 'created_at', 'last_updated']:
                use_context_model = True
            else:
                use_context_model = False

            if sort_direction == "desc":
                sort_field = "-" + sort_field

            logger.debug("***  sorting %s" % sort_field)

            if use_context_model:
                contexts = contexts.order_by(sort_field)
            else:
                # we can't do ordering directly on context model

                self.custom_ordering = sort_field

        logger.debug("found %s contexts for initial query" % contexts.count())
        return contexts

    def _get_grid_field_display_name(self, context_model):
        registry_code = context_model.registry.code
        patient_id = context_model.content_object.pk

        return "<a href='%s'>%s</a>" % (reverse("context_edit", kwargs={"registry_code": registry_code,
                                                                        "patient_id": patient_id,
                                                                        "context_id": context_model.pk,
                                                                        }),
                                        context_model.display_name)

    def _get_grid_field_working_groups_display(self, context_model):
        patient_model = context_model.content_object
        return patient_model.working_groups_display


    def _get_grid_field_context_menu(self, context_model):
        patient_model = context_model.content_object
        context_menu = PatientContextMenu(self.user,
                                          self.registry_model,
                                          self.form_progress,
                                          patient_model,
                                          context_model)
        return context_menu.menu_html

    def _get_grid_field_created_at(self, context_model):
        return str(context_model.created_at)

    def _get_grid_field_date_of_birth(self, context_model):
        patient_model = context_model.content_object
        return str(patient_model.date_of_birth)

    def _get_grid_field_patient_link(self, context_model):
        patient_model = context_model.content_object
        registry_code = self.registry_model.code
        return "<a href='%s'>%s</a>" % \
               (reverse("patient_edit",
                        kwargs={"registry_code": registry_code,
                                "patient_id": patient_model.id}),
                patient_model.display_name)

    def _get_grid_field_diagnosis_progress(self, context_model):
        patient_model = context_model.content_object
        progress_number = self.form_progress.get_group_progress("diagnosis", patient_model, context_model)
        template = "<div class='progress'><div class='progress-bar progress-bar-custom' role='progressbar'" + \
                   " aria-valuenow='%s' aria-valuemin='0' aria-valuemax='100' style='width: %s%%'>" + \
                   "<span class='progress-label'>%s%%</span></div></div>"

        return template % (progress_number, progress_number, progress_number)

    def _get_grid_field_diagnosis_currency(self, context_model):
        patient_model = context_model.content_object
        diagnosis_currency = self.form_progress.get_group_currency("diagnosis", patient_model)
        icon = "ok" if diagnosis_currency else "remove"
        color = "green" if diagnosis_currency else "red"
        return "<span class='glyphicon glyphicon-%s' style='color:%s'></span>" % (icon, color)


    def _get_grid_field_genetic_data_map(self, context_model):
        patient_model = context_model.content_object
        has_genetic_data = self.form_progress.get_group_has_data("genetic", patient_model, context_model)
        icon = "ok" if has_genetic_data else "remove"
        color = "green" if has_genetic_data else "red"
        return "<span class='glyphicon glyphicon-%s' style='color:%s'></span>" % (icon, color)

    def _apply_filter(self, queryset, search_phrase):
        context_filter = Q(display_name__icontains=search_phrase)
        patient_filter = Q(given_names__icontains=search_phrase) | \
                         Q(family_name__icontains=search_phrase)

        matching_patients = Patient.objects.filter(rdrf_registry__in=[self.registry_model]).filter(patient_filter)

        return queryset.filter(context_filter | Q(object_id__in=[p.pk for p in matching_patients]))


class ContextsListingView(LoginRequiredMixin, View):

    def get(self, request):
        if request.user.is_patient:
            raise PermissionDenied()

        context = {}
        context.update(csrf(request))
        registry_model = None

        registry_code = request.GET.get("registry_code", None)
        if registry_code is not None:
            try:
                registry_model = Registry.objects.get(code=registry_code)
            except Registry.DoesNotExist:
                return HttpResponseRedirect("/")

        if registry_model is None:
            if request.user.is_superuser:
                registries = [registry_model for registry_model in Registry.objects.all()]
            else:
                registries = [registry_model for registry_model in request.user.registry.all()]
        else:
            registries = [registry_model]

        patient_id = request.GET.get("patient_id", None)

        if patient_id is not None:
            if not self._allowed(request.user, registry_model, patient_id):
                return HttpResponseRedirect("/")

        context_form_group_id = request.GET.get("context_form_group_id", None)
        

        context["registries"] = registries
        context["location"] = "Context List"
        context["patient_id"] = patient_id
        context["context_form_group_id"] = context_form_group_id
        context["registry_code"] = registry_code

        columns = []

        sorted_by_order = sorted(settings.GRID_CONTEXT_LISTING, key=itemgetter('order'), reverse=False)

        for definition in sorted_by_order:
            if request.user.is_superuser or definition["access"]["default"] or \
                    request.user.has_perm(definition["access"]["permission"]):
                columns.append(
                    {
                        "data" : definition["data"],
                        "label" : definition["label"]
                    }
                )

        context["columns"] = columns

        template = 'rdrf_cdes/contexts_no_registries.html' if len(registries) == 0 else 'rdrf_cdes/contexts.html'

        return render_to_response(
            template,
            context,
            context_instance=RequestContext(request))

    def _allowed(self, user, registry_model, patient_id):
        return True  #todo restrict


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
    def get(self, request, registry_code, patient_id, context_id=None):
        if not request.user.is_authenticated():
            consent_form_url = reverse('consent_form_view', args=[registry_code, patient_id])
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
                                  context_id,
                                  None)

        try:
            parent = ParentGuardian.objects.get(user=request.user)
        except ParentGuardian.DoesNotExist:
            parent = None

        context_launcher = RDRFContextLauncherComponent(request.user,
                                                        registry_model,
                                                        patient_model,
                                                        current_form_name="Consents")

        


        context = {
            "location": "Consents",
            "forms": form_sections,
            "context_id": context_id,
            "patient": patient_model,
            "patient_id": patient_model.id,
            "registry_code": registry_code,
            'patient_link': PatientLocator(registry_model, patient_model).link,
            "context_launcher": context_launcher.html,
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
        return reverse("consent_form_view", args=[registry_model.code,
                                                  patient_model.pk])

    def post(self, request, registry_code, patient_id, context_id=None):
        logger.debug("******************** post of consents *********************")
        if not request.user.is_authenticated():
            consent_form_url = reverse('consent_form_view', args=[registry_code, patient_id, context_id])
            login_url = reverse('login')
            return redirect("%s?next=%s" % (login_url, consent_form_url))

        registry_model = Registry.objects.get(code=registry_code)
        patient_model = Patient.objects.get(id=patient_id)
        context_launcher = RDRFContextLauncherComponent(request.user,
                                                        registry_model,
                                                        patient_model,
                                                        current_form_name="Consents")

        wizard = NavigationWizard(request.user,
                                  registry_model,
                                  patient_model,
                                  NavigationFormType.CONSENTS,
                                  context_id,
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
            'patient_link': PatientLocator(registry_model, patient_model).link,
            "context_id": context_id,
            "registry_code": registry_code,
            "next_form_link": wizard.next_link,
            "previous_form_link": wizard.previous_link,
            "context_launcher": context_launcher.html,
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
