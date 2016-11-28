from django.shortcuts import render, get_object_or_404
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
from .models import RegistryForm, Registry, QuestionnaireResponse
from .models import Section, CommonDataElement
from registry.patients.models import Patient, ParentGuardian
from .dynamic_forms import create_form_class_for_section
from .dynamic_data import DynamicDataWrapper
from django.http import Http404
from .questionnaires import PatientCreator
from .file_upload import wrap_gridfs_data_for_form
from .file_upload import wrap_file_cdes
from . import filestorage
from .utils import de_camelcase
from rdrf.utils import location_name, is_multisection, mongo_db_name, make_index_map
from rdrf.mongo_client import construct_mongo_client
from rdrf.wizard import NavigationWizard, NavigationFormType
from rdrf.models import RDRFContext

from rdrf.consent_forms import CustomConsentFormGenerator
from rdrf.utils import consent_status_for_patient

from rdrf.contexts_api import RDRFContextManager, RDRFContextError

from django.shortcuts import redirect
from django.forms.models import inlineformset_factory
from registry.patients.models import PatientConsent
from registry.patients.admin_forms import PatientConsentFileForm
from django.utils.translation import ugettext as _

import json
import os
from collections import OrderedDict
from django.conf import settings
from rdrf.actions import ActionExecutor
from rdrf.models import AdjudicationRequest, AdjudicationRequestState, AdjudicationError, AdjudicationDefinition, Adjudication
from rdrf.utils import FormLink
from registry.groups.models import CustomUser
import logging
from registry.groups.models import WorkingGroup
from rdrf.dynamic_forms import create_form_class_for_consent_section
from rdrf.form_progress import FormProgress

from rdrf.contexts_api import RDRFContextError
from rdrf.locators import PatientLocator
from rdrf.components import RDRFContextLauncherComponent
from rdrf.questionnaires import PatientCreatorError


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


class SectionInfo(object):
    """
    Info to store a section.
    Used so we save everything after all sections have validated.
    """

    def __init__(self, patient_wrapper, is_multiple, registry_code, collection_name, data, index_map=None):
        self.patient_wrapper = patient_wrapper
        self.is_multiple = is_multiple
        self.registry_code = registry_code
        self.collection_name = collection_name
        self.data = data
        self.index_map = index_map

    def save_to_mongo(self):
        if not self.is_multiple:
            self.patient_wrapper.save_dynamic_data(self.registry_code, self.collection_name, self.data)
        else:
            self.patient_wrapper.save_dynamic_data(self.registry_code,
                                                   self.collection_name,
                                                   self.data,
                                                   multisection=True,
                                                   index_map=self.index_map)


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

        except RDRFContextError as ex:
            logger.error("Error setting rdrf context id %s for patient %s in %s: %s" % (context_id,
                                                                                        patient_model,
                                                                                        self.registry,
                                                                                        ex))

            raise RDRFContextSwitchError

    def _enable_context_creation_after_save(self,
                                            request,
                                            registry_code,
                                            form_id,
                                            patient_id):
        # Enable only if:
        #   the form is the only member of a context form group marked as multiple
        user = request.user
        registry_model = Registry.objects.get(code=registry_code)
        form_model = RegistryForm.objects.get(id=form_id)
        patient_model = Patient.objects.get(id=patient_id)

        if not registry_model.has_feature("contexts"):
            raise Http404

        if not patient_model.in_registry(registry_model.code):
            raise Http404

        if not user.can_view(form_model):
            raise Http404

        # is this form the only member of a multiple form group?
        form_group = None
        for cfg in registry_model.multiple_form_groups:
            form_models = cfg.form_models
            if len(form_models) == 1 and form_models[0].pk == form_model.pk:
                form_group = cfg
                break

        if form_group is None:
            raise Http404

        self.create_mode_config = {
            "form_group": form_group,
        }

        self.CREATE_MODE = True

    @login_required_method
    def get(self, request, registry_code, form_id, patient_id, context_id=None):
        # RDR-1398 enable a Create View which context_id of 'add' is provided
        self.CREATE_MODE = False  # Normal edit view; False means Create View and context saved AFTER validity check
        if context_id == 'add':
            self._enable_context_creation_after_save(request,
                                                     registry_code,
                                                     form_id,
                                                     patient_id)

        if request.user.is_working_group_staff:
            raise PermissionDenied()
        self.user = request.user
        self.form_id = form_id
        self.patient_id = patient_id

        try:
            patient_model = Patient.objects.get(pk=patient_id)
        except Patient.DoesNotExist:
            raise Http404

        self.registry = self._get_registry(registry_code)

        self.rdrf_context_manager = RDRFContextManager(self.registry)

        try:
            if not self.CREATE_MODE:
                self.set_rdrf_context(patient_model, context_id)
        except RDRFContextSwitchError:
            return HttpResponseRedirect("/")

        if not self.CREATE_MODE:
            rdrf_context_id = self.rdrf_context.pk
            logger.debug("********** RDRF CONTEXT ID SET TO %s" % rdrf_context_id)

            self.dynamic_data = self._get_dynamic_data(id=patient_id,
                                                       registry_code=registry_code,
                                                       rdrf_context_id=rdrf_context_id)
        else:
            rdrf_context_id = "add"
            self.dynamic_data = None

        self.registry_form = self.get_registry_form(form_id)

        context_launcher = RDRFContextLauncherComponent(request.user,
                                                        self.registry,
                                                        patient_model,
                                                        self.registry_form.name,
                                                        self.rdrf_context)

        context = self._build_context(user=request.user, patient_model=patient_model)
        context["location"] = location_name(self.registry_form, self.rdrf_context)
        context["header"] = self.registry_form.header
        if not self.CREATE_MODE:
            context["CREATE_MODE"] = False
            context["show_print_button"] = True
        else:
            context["CREATE_MODE"] = True
            context["show_print_button"] = False

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
        return render(request, self._get_template(), context)

    def _get_field_ids(self, form_class):
        # the ids of each cde on the form
        return ",".join(form_class().fields.keys())

    @login_required_method
    def post(self, request, registry_code, form_id, patient_id, context_id=None):
        all_errors = []
        progress_dict = {}

        self.CREATE_MODE = False  # Normal edit view; False means Create View and context saved AFTER validity check
        sections_to_save = []  # when a section is validated it is added to this list
        all_sections_valid = True
        if context_id == 'add':
            # The following switches on CREATE_MODE if conditions satisfied
            self._enable_context_creation_after_save(request,
                                                     registry_code,
                                                     form_id,
                                                     patient_id)
        if request.user.is_superuser:
            pass
        elif request.user.is_working_group_staff or request.user.has_perm("rdrf.form_%s_is_readonly" % form_id):
            raise PermissionDenied()

        self.user = request.user

        registry = Registry.objects.get(code=registry_code)
        self.registry = registry

        patient = Patient.objects.get(pk=patient_id)
        self.patient_id = patient_id

        self.rdrf_context_manager = RDRFContextManager(self.registry)

        try:
            if not self.CREATE_MODE:
                self.set_rdrf_context(patient, context_id)
        except RDRFContextSwitchError:
            return HttpResponseRedirect("/")

        if not self.CREATE_MODE:
            dyn_patient = DynamicDataWrapper(patient, rdrf_context_id=self.rdrf_context.pk)
        else:
            dyn_patient = DynamicDataWrapper(patient, rdrf_context_id='add')

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
                    # save all sections ONLY is all valid!
                    sections_to_save.append(SectionInfo(dyn_patient, False, registry_code, "cdes", dynamic_data))
                    current_data = dyn_patient.load_dynamic_data(self.registry.code, "cdes")
                    form_data = wrap_file_cdes(registry_code, dynamic_data, current_data, multisection=False)
                    form_section[s] = form_class(dynamic_data, initial=form_data)
                else:
                    logger.debug("form is invalid")
                    all_sections_valid = False
                    for e in form.errors:
                        error_count += 1
                        all_errors.append(e)

                    from rdrf.utils import wrap_uploaded_files
                    request.POST.update(request.FILES)

                    form_section[s] = form_class(wrap_uploaded_files(registry_code, request.POST), request.FILES)

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
                    to_remove = [i for i, d in enumerate(dynamic_data) if d.get('DELETE')]
                    index_map = make_index_map(to_remove, len(dynamic_data))

                    for i in reversed(to_remove):
                        del dynamic_data[i]

                    section_dict = {s: dynamic_data}
                    sections_to_save.append(SectionInfo(dyn_patient, True, registry_code,
                                                        "cdes", section_dict, index_map))

                    current_data = dyn_patient.load_dynamic_data(self.registry.code, "cdes")

                    form_data = wrap_file_cdes(registry_code, dynamic_data, current_data, multisection=True)

                    form_section[s] = form_set_class(initial=form_data, prefix=prefix)

                else:
                    all_sections_valid = False
                    logger.debug("multisection formset is invalid")
                    for e in formset.errors:
                        error_count += 1
                        all_errors.append(e)
                    form_section[s] = form_set_class(request.POST, request.FILES, prefix=prefix)

        # Save one snapshot after all sections have being persisted
        if all_sections_valid:
            for section_info in sections_to_save:
                section_info.save_to_mongo()

            progress_dict = dyn_patient.save_form_progress(registry_code, context_model=self.rdrf_context)

            dyn_patient.save_snapshot(registry_code, "cdes")

            if self.CREATE_MODE and dyn_patient.rdrf_context_id != "add":
                # we've created the context on the fly so no redirect to the edit view on the new context
                newly_created_context = RDRFContext.objects.get(id=dyn_patient.rdrf_context_id)
                dyn_patient.save_form_progress(registry_code, context_model=newly_created_context)

                return HttpResponseRedirect(reverse('registry_form', args=(registry_code,
                                                                           form_id,
                                                                           patient.pk,
                                                                           newly_created_context.pk)))

            if dyn_patient.rdrf_context_id == "add":
                raise Exception("Content not created")
        else:
            for e in all_errors:
                logger.debug("validation Error: %s" % e)

        patient_name = '%s %s' % (patient.given_names, patient.family_name)
        # progress saved to progress collection in mongo
        # the data is returned also

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
            'CREATE_MODE': self.CREATE_MODE,
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
            "show_print_button": True if not self.CREATE_MODE else False,
            "context_launcher": context_launcher.html,
            "have_dynamic_data": all_sections_valid,
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


            context["form_progress_cdes"]  = progress_dict.get(self.registry_form.name + "_form_cdes_status",
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

        return render(request, self._get_template(), context)

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
            'CREATE_MODE': self.CREATE_MODE,
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
            "has_form_progress": self.registry_form.has_progress_indicator,
            "have_dynamic_data": bool(self.dynamic_data),
        }

        if not self.registry_form.is_questionnaire and self.registry_form.has_progress_indicator:

            form_progress = FormProgress(self.registry_form.registry)

            form_progress_percentage = form_progress.get_form_progress(self.registry_form,
                                                                       patient_model,
                                                                       self.rdrf_context)

            form_cdes_status = form_progress.get_form_cdes_status(self.registry_form,
                                                                  patient_model,
                                                                  self.rdrf_context)

            context["form_progress"] = form_progress_percentage
            context["form_progress_cdes"] =  form_cdes_status

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
        from .utils import id_on_page
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
                messages.append(_("Consent Section Invalid"))

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
        self.CREATE_MODE = False

    from .patient_decorators import patient_has_access

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
        return render(request, 'rdrf_cdes/questionnaire_error.html', context)

    def _get_template(self):
        return "rdrf_cdes/questionnaire.html"

    def _get_prelude(self, registry_code, questionnaire_context):
        if questionnaire_context is None:
            prelude_file = "prelude_%s.html" % registry_code
        else:
            prelude_file = "prelude_%s_%s.html" % (registry_code, questionnaire_context)

        file_path = os.path.join(settings.TEMPLATES[0]["DIRS"][0], 'rdrf_cdes', prelude_file)
        logger.debug("file path = %s" % file_path)
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
                        registry_code, "cdes", data_map[section], multisection=True,
                        additional_data={"questionnaire_context": self.questionnaire_context})
                else:
                    questionnaire_response_wrapper.save_dynamic_data(
                        registry_code, "cdes", data_map[section],
                        additional_data={"questionnaire_context": self.questionnaire_context})

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

            return render(request, 'rdrf_cdes/completed_questionnaire_thankyou.html', context)
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
                _('The questionnaire was not submitted because of validation errors - please try again'))
            return render(request, 'rdrf_cdes/questionnaire.html', context)

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
        context["form_model"] = context["registry_model"].questionnaire
        context["qr_model"] = QuestionnaireResponse.objects.get(id=questionnaire_response_id)
        context["patient_lookup_url"] = reverse("patient_lookup", args=(registry_code,))

        context["questionnaire"] = Questionnaire(context["registry_model"],
                                                 context["qr_model"])

        context.update(csrf(request))

        return render(request, template_name, context)

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
        return render(request, template, context)

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
        return render(request, self.TEMPLATE, context)


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
        return render(request, 'rdrf_cdes/rdrf-designer.html', context)


class RDRFDesignerRegistryStructureEndPoint(View):

    def get(self, request, reg_pk):
        try:
            registry = Registry.objects.get(pk=reg_pk)
            data = registry.structure
        except Registry.DoesNotExist:
            data = {}

        return HttpResponse(json.dumps(data), content_type="application/json")

    def post(self, request, reg_pk):
        try:
            registry_structure = json.loads(request.body.decode("utf-8"))
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
        action_dict = json.loads(request.body.decode("utf-8"))
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
            return StandardView.render_error(request, _("Adjudication Definition not found!"))

        try:
            patient = Patient.objects.get(pk=patient_id)
        except Patient.DoesNotExist:
            return StandardView.render_error(
                request,
                _("Patient with id %s not found!") %
                patient_id)

        context = adj_def.create_adjudication_inititiation_form_context(patient)
        context.update(csrf(request))
        return render(request, 'rdrf_cdes/adjudication_initiation_form.html', context)

    @login_required_method
    def post(self, request, def_id, patient_id):
        try:
            adj_def = AdjudicationDefinition.objects.get(pk=def_id)
        except AdjudicationDefinition.DoesNotExist:
            return StandardView.render_error(
                request,
                _("Adjudication Definition %s not found") %
                def_id)

        try:
            patient = Patient.objects.get(pk=patient_id)
        except Patient.DoesNotExist:
            return StandardView.render_error(
                request,
                _("Patient with id %s not found!") %
                patient_id)

        from rdrf.models import AdjudicationState
        adjudication_state = adj_def.get_state(patient)
        if adjudication_state == AdjudicationState.ADJUDICATED:
            return StandardView.render_error(
                request,
                _("This patient has already been adjudicated!"))
        elif adjudication_state == AdjudicationState.UNADJUDICATED:
            return StandardView.render_error(
                request,
                _("This patient has already had an adjudication initiated"))
        elif adjudication_state != AdjudicationState.NOT_CREATED:
            return StandardView.render_error(
                request,
                _("Unknown adjudication state '%s' - contact admin") %
                adjudication_state)
        else:
            # no requests have been adjudication requests created for this patient
            sent_ok, errors = self._create_adjudication_requests(
                request, adj_def, patient, request.user)
            if errors:
                return StandardView.render_error(
                    request,
                    _("Adjudication Requests created OK for users: %(sent_ok)s.<p>But the following errors occurred: %(errors)s") %
                    {"sent_ok": sent_ok, "errors": errors})
            else:
                return StandardView.render_information(
                    request,
                    _("Adjudication Request Sent Successfully!"))

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
                _("Adjudication already created for this patient and definition"))

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
                errors.append(_("Could not find user for %s: %s") % (target_username, ex))
                continue

            if not target_user:
                errors.append(_("Could not find user for %s") % target_username)
                continue
            else:
                try:
                    adjudication_definition.create_adjudication_request(
                        request, requesting_user, patient, target_user)
                    request_created_ok.append(target_username)
                except Exception as ex:
                    errors.append(
                        _("Could not create adjudication request object for %(target_user)s: %(ex)s") %
                        {"target_user": target_user, "ex": ex})

        for target_working_group_name in target_working_group_names:
            try:
                target_working_group = WorkingGroup.objects.get(name=target_working_group_name)
            except WorkingGroup.DoesNotExist:
                errors.append(_("There is no working group called %s") % target_working_group_name)
                continue

            for target_user in target_working_group.users:
                try:
                    adjudication_definition.create_adjudication_request(
                        requesting_user, patient, target_user)
                    request_created_ok.append(target_username)
                except Exception as ex:
                    errors.append(
                        _("could not create adjudication request for %(target_user)s in group %(target_working_group)s:%(ex)s") %
                        {"target_user": target_user, "target_working_group": target_working_group, "ex": ex})
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
            msg = _("Adjudication request not found or not for current user or has already been actioned")
            return StandardView.render_error(request, msg)

        if adj_req.decided:
            # The adjudicator has already acted on the information from other requests
            # for this patient
            return StandardView.render_information(
                request, _("An adjudicator has already made a decision regarding this adjudication - it can no longer be voted on"))

        adjudication_form, datapoints = adj_req.create_adjudication_form()

        context = {"adjudication_form": adjudication_form,
                   "datapoints": datapoints,
                   "req": adj_req}

        context.update(csrf(request))
        return render(request, 'rdrf_cdes/adjudication_form.html', context)

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
                    return StandardView.render_error(request, _("Adjudication Error: %s") % aerr)

                return StandardView.render_information(
                    request,
                    _("Adjudication Response submitted successfully!"))

            except AdjudicationRequest.DoesNotExist:
                msg = _("Cannot submit adjudication - adjudication request with id %s not found") %  \
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
            return Http404(_("Adjudication definition not found"))

        adjudicating_username = adj_def.adjudicator_username

        if adjudicating_username != request.user.username:
            return StandardView.render_error(
                request,
                _("This adjudication result is not adjudicable by you!"))

        try:
            from registry.groups.models import CustomUser
            requesting_user = CustomUser.objects.get(pk=requesting_user_id)
        except CustomUser.DoesNotExist:
            return StandardView.render_error(
                request,
                _("Could not find requesting user for this adjudication '%s'") %
                requesting_user_id)

        try:
            adjudication = Adjudication.objects.get(
                definition=adj_def,
                patient_id=patient_id,
                requesting_username=requesting_user.username)
        except Adjudication.DoesNotExist:
            msg = _("Could not find adjudication for definition %(adj_def)s patient %(patient_id)s requested by %(requesting_user)s") % {
                "adj_def": adj_def, "patient_id": patient_id, "requesting_user": requesting_user}

            return StandardView.render_error(request, msg)

        stats, adj_responses = self._get_stats_and_responses(
            patient_id, requesting_user.username, adj_def)
        if len(adj_responses) == 0:
            msg = _("No one has responded to the adjudication request yet!- stats are %s") % stats
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
                    list(map(float, values))
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
                    return list(map(float, values))
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
                    "labels": list(histogram.keys()),
                    "datasets": [
                        {
                            "label": self.label,
                            "fillColor": "rgba(220,220,220,0.5)",
                            "strokeColor": "rgba(220,220,220,0.8)",
                            "highlightFill": "rgba(220,220,220,0.75)",
                            "highlightStroke": "rgba(220,220,220,1)",
                            "data": list(histogram.values())
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
        return render(request, 'rdrf_cdes/adjudication_results.html', context)

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
            msg = _("Adjudication Definition with id %s not found") % adjudication_definition_id
            return StandardView.render_error(request, msg)

        if adj_def.adjudicator_username != request.user.username:
            return StandardView.render_error(
                request,
                _("You are not authorised to submit an adjudication for this patient"))

        patient_id_on_form = request.POST["patient_id"]
        if patient_id_on_form != patient_id:
            return StandardView.render_error(request, _("patient incorrect!"))

        try:
            requesting_user = CustomUser.objects.get(pk=requesting_user_id)
        except CustomUser.DoesNotExist:
            return StandardView.render_error(request, _("requesting user cannot be found"))

        try:
            patient = Patient.objects.get(pk=patient_id)
        except Patient.DoesNotExist:
            return StandardView.render_error(request, _("Patient does not exist"))

        adjudication_state = adj_def.get_state(patient)

        if adjudication_state == AdjudicationState.NOT_CREATED:
            # No requests have been sent out for this definiton
            msg = _("No Adjudication requests have come back for this patient - it cannot be decided yet!")
            return StandardView.render_information(request)

        elif adjudication_state == AdjudicationState.ADJUDICATED:
            return StandardView.render_error(
                request,
                _("This patient has already been adjudicated!"))
        elif adjudication_state != AdjudicationState.UNADJUDICATED:
            return StandardView.render_error(
                request,
                _("Unknown adjudication state: %s") %
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
                return StandardView.render_error(request, _("Adjudication object doesn't exist"))

            adjudication.decision = adj_dec
            adjudication.save()
            result = adjudication.perform_actions(request)
            if result.ok:
                return StandardView.render_information(
                    request,
                    _("Your adjudication decision has been sent to %s") %
                    adjudication.requesting_username)
            else:
                return StandardView.render_error(
                    request,
                    _("Your adjudication decision was not communicated: %s") %
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


class ConstructorFormView(View):

    def get(self, request, form_name):
        return render(request, 'rdrf_cdes/%s.html' % form_name)


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
            "form_name": "fixme",  # required for form_print link
            "patient": patient_model,
            "patient_id": patient_model.id,
            "registry_code": registry_code,
            'patient_link': PatientLocator(registry_model, patient_model).link,
            "context_launcher": context_launcher.html,
            "next_form_link": wizard.next_link,
            "previous_form_link": wizard.previous_link,
            "parent": parent,
            "consent": consent_status_for_patient(registry_code, patient_model),
            "show_print_button": True,
        }

        logger.debug("context = %s" % context)

        logger.debug("******************** rendering get *********************")
        return render(request, "rdrf_cdes/custom_consent_form.html", context)

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

        patient_section_consent_file = ("Upload consent file (if requested)", None)

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

        # return form_sections

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
        patient_section_consent_file = ("Upload consent file (if requested)", None)

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

        return render(request, "rdrf_cdes/custom_consent_form.html", context)
