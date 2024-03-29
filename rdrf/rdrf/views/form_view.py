from django.shortcuts import render, get_object_or_404
from django.views.generic.base import View, TemplateView
from django.template.context_processors import csrf
from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.http import HttpResponse, FileResponse
from django.http import HttpResponseRedirect, HttpResponseNotFound
from django.forms.formsets import formset_factory
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from rdrf.models.definition.models import RegistryForm, Registry, QuestionnaireResponse
from rdrf.models.definition.models import Section, CommonDataElement, ClinicalData
from registry.patients.models import Patient, ParentGuardian
from rdrf.forms.dynamic.dynamic_forms import create_form_class_for_section
from rdrf.db.dynamic_data import DynamicDataWrapper
from django.http import Http404
from rdrf.forms.file_upload import wrap_fs_data_for_form
from rdrf.forms.file_upload import wrap_file_cdes
from rdrf.db import filestorage
from rdrf.helpers.utils import (
    de_camelcase,
    location_name,
    is_multisection,
    make_index_map,
)
from rdrf.helpers.utils import parse_iso_date
from rdrf.views.decorators.patient_decorators import patient_questionnaire_access
from rdrf.forms.navigation.wizard import NavigationWizard, NavigationFormType
from rdrf.models.definition.models import RDRFContext
from rdrf.custom_signals import clinical_data_saved_ok

from rdrf.forms.consent_forms import CustomConsentFormGenerator
from rdrf.helpers.utils import consent_status_for_patient
from rdrf.helpers.utils import anonymous_not_allowed

from rdrf.db.contexts_api import RDRFContextManager
from rdrf.db.contexts_api import RDRFContextError
from explorer.utils import create_field_values


from django.shortcuts import redirect
from django.forms.models import inlineformset_factory
from registry.patients.models import PatientConsent
from registry.patients.admin_forms import PatientConsentFileForm
from django.utils.translation import ugettext as _

import json
import os
from collections import OrderedDict
from django.conf import settings
from rdrf.services.rpc.actions import ActionExecutor
from rdrf.helpers.utils import FormLink
from rdrf.forms.dynamic.dynamic_forms import create_form_class_for_consent_section
from rdrf.forms.progress.form_progress import FormProgress

from rdrf.forms.navigation.locators import PatientLocator
from rdrf.forms.components import RDRFContextLauncherComponent
from rdrf.forms.components import RDRFPatientInfoComponent
from rdrf.security.security_checks import security_check_user_patient

from rdrf.helpers.utils import annotate_form_with_verifications

from rdrf.views.custom_actions import CustomActionWrapper

import logging

logger = logging.getLogger(__name__)
login_required_method = method_decorator(login_required)


class RDRFContextSwitchError(Exception):
    pass


class LoginRequiredMixin(object):
    @login_required_method
    def dispatch(self, request, *args, **kwargs):
        return super(LoginRequiredMixin, self).dispatch(request, *args, **kwargs)


class CustomConsentHelper(object):
    def __init__(self, registry_model):
        self.registry_model = registry_model
        self.custom_consent_errors = {}
        self.custom_consent_data = None
        self.custom_consent_keys = []
        self.custom_consent_wrappers = []
        self.error_count = 0

    def create_custom_consent_wrappers(self):

        for consent_section_model in self.registry_model.consent_sections.order_by(
            "code"
        ):
            consent_form_class = create_form_class_for_consent_section(
                self.registry_model, consent_section_model
            )
            consent_form = consent_form_class(data=self.custom_consent_data)
            consent_form_wrapper = ConsentFormWrapper(
                consent_section_model.section_label, consent_form, consent_section_model
            )

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
                self.custom_consent_errors[custom_consent_wrapper.label] = [
                    error_message for error_message in custom_consent_wrapper.errors
                ]
                self.error_count += custom_consent_wrapper.num_errors

    def load_dynamic_data(self, dynamic_data):
        # load data from Mongo
        self.custom_consent_data = dynamic_data.get("custom_consent_data", None)


class SectionInfo(object):
    """
    Info to store a section ( and create section forms)

    Used so we save everything _after_ all sections have validated.
    Also the file upload links weren't being created post save for the POST response
    because the forms had already been instantiated and "wrapped" too early.

    """

    def __init__(
        self,
        section_code,
        patient_wrapper,
        is_multiple,
        registry_code,
        collection_name,
        data,
        index_map=None,
        form_set_class=None,
        form_class=None,
        prefix=None,
        form_name=None,
    ):
        self.section_code = section_code
        self.patient_wrapper = patient_wrapper
        self.is_multiple = is_multiple
        self.registry_code = registry_code
        self.registry = Registry.objects.get(code=registry_code)
        self.use_new_style_calcs = self.registry.has_feature("use_new_style_calcs")
        self.collection_name = collection_name
        self.data = data
        self.index_map = index_map
        # if this section is not a multisection this form class is used to create the form
        self.form_class = form_class
        # otherwise we create a formset using these
        self.form_set_class = form_set_class
        self.prefix = prefix
        self.form_name = form_name

    def update_calculated_fields(self):
        for key in self.data:
            try:
                form_name, section_code, cde_code = key.split("____")
            except ValueError:
                continue

            cde_model = CommonDataElement.objects.get(code=cde_code)
            if cde_model.datatype == "calculated":
                patient = self._get_patient_dict()
                calculation_context = self._get_calculation_context(cde_model)
                new_value = cde_model.calculate(patient, calculation_context)
                self.data[key] = new_value

    def _get_patient_dict(self):
        patient: Patient = self.patient_wrapper.obj
        # this mirrors what old API call creates
        patient_dict = {
            "date_of_birth": patient.date_of_birth,
            "patient_id": patient.id,
            "registry_code": self.registry_code,
            "sex": patient.sex,
        }
        return patient_dict

    def _get_calculation_context(self, cde_model):
        from rdrf.forms.fields import calculated_functions as calcs_module

        input_function_name = f"{cde_model.code}_inputs"
        calculation_context = {}
        if hasattr(calcs_module, input_function_name):
            input_function = getattr(calcs_module, input_function_name)
            if callable(input_function):
                input_cde_codes = input_function()
                for input_cde_code in input_cde_codes:
                    input_value = self._get_input_value(input_cde_code)
                    if input_value is not None:
                        calculation_context[input_cde_code] = input_value
        else:
            raise Exception("No input for calc")

        return calculation_context

    def _get_input_value(self, cde_code):
        for key in self.data:
            if key.endswith("____" + cde_code):
                return self.data[key]

        # non-local field value

    def save(self):
        if not self.is_multiple:
            if self.use_new_style_calcs:
                self.update_calculated_fields()
            self.patient_wrapper.save_dynamic_data(
                self.registry_code, self.collection_name, self.data
            )
        else:
            self.patient_wrapper.save_dynamic_data(
                self.registry_code,
                self.collection_name,
                self.data,
                multisection=True,
                index_map=self.index_map,
            )

    def recreate_form_instance(self):
        # called when all sections on a form are valid
        # We do this to create a form instance which has correct links to uploaded files
        current_data = self.patient_wrapper.load_dynamic_data(
            self.registry_code, "cdes"
        )
        if self.is_multiple:
            # the cleaned data from the form submission
            dynamic_data = self.data[self.section_code]
        else:
            dynamic_data = self.data

        wrapped_data = wrap_file_cdes(
            self.registry_code,
            dynamic_data,
            current_data,
            multisection=self.is_multiple,
        )

        if self.is_multiple:
            form_instance = self.form_set_class(
                initial=wrapped_data, prefix=self.prefix
            )
        else:
            form_instance = self.form_class(dynamic_data, initial=wrapped_data)

        return form_instance

    @property
    def cde_models(self):
        cdes = []
        section_code = self.section_code
        form_model = self.patient_wrapper.current_form_model
        for section_model in form_model.section_models:
            if section_model.code == section_code:
                for cde_model in section_model.cde_models:
                    cdes.append(cde_model)
        return cdes


class FormSwitchLockingView(View):
    @method_decorator(anonymous_not_allowed)
    @login_required_method
    def get(self, request, registry_code, form_id, patient_id, context_id=None):

        # Switch the locking.
        context_model = RDRFContext.objects.get(id=context_id)
        form_model = RegistryForm.objects.get(id=form_id)
        form_name = form_model.name

        if not request.user.is_authenticated or not request.user.has_perm(
            "rdrf.form_%s_can_lock" % form_model.name
        ):
            logger.warning(
                f"User {request.user.id} ({request.user}) is trying to lock/unlock the form {form_model.name} \
                for context {context_model.id} - patient {patient_id} without the permission!"
            )
            raise Exception("You don't have the permission to lock/unlock this form.")

        # the clinical metadata are only stored with the cdes collection
        try:
            clinical_data = ClinicalData.objects.get(
                registry_code=registry_code,
                collection="cdes",
                django_id=patient_id,
                django_model="Patient",
                context_id=context_id,
            )
            clinical_data.switch_metadata_locking(form_name)
        except ClinicalData.DoesNotExist:
            # Not ClinicalData means the form is not save yet, just ignore the command.
            pass

        return HttpResponseRedirect(
            reverse(
                "registry_form", args=[registry_code, form_id, patient_id, context_id]
            )
        )


class FormView(View):
    def __init__(self, *args, **kwargs):
        # when set to True in integration testing, switches off unsupported messaging middleware
        self.template = None
        self.registry = None
        self.dynamic_data = {}
        self.registry_form = None
        self.form_id = None
        self.patient_id = None
        self.user = None
        self.rdrf_context = None
        self.show_multisection_delete_checkbox = True

        super(FormView, self).__init__(*args, **kwargs)

    def _get_registry(self, registry_code):
        try:
            return Registry.objects.get(code=registry_code)

        except Registry.DoesNotExist:
            raise Http404("Registry %s does not exist" % registry_code)

    def _get_dynamic_data(
        self, registry_code=None, rdrf_context_id=None, model_class=Patient, id=None
    ):
        obj = model_class.objects.get(pk=id)
        dyn_obj = DynamicDataWrapper(obj, rdrf_context_id=rdrf_context_id)
        dynamic_data = dyn_obj.load_dynamic_data(registry_code, "cdes")
        return dynamic_data

    def set_rdrf_context(self, patient_model, context_id):
        # Ensure we always have a context , otherwise bail
        self.rdrf_context = None
        try:
            if context_id is None:
                if self.registry.has_feature("contexts"):
                    raise RDRFContextError(
                        "Registry %s supports contexts but no context id  passed in url"
                        % self.registry
                    )
                else:
                    self.rdrf_context = (
                        self.rdrf_context_manager.get_or_create_default_context(
                            patient_model
                        )
                    )
            else:
                self.rdrf_context = self.rdrf_context_manager.get_context(
                    context_id, patient_model
                )

            if self.rdrf_context is None:
                raise RDRFContextSwitchError

        except RDRFContextError as ex:
            logger.error(
                "Error setting rdrf context id %s for patient %s in %s: %s"
                % (
                    context_id,
                    getattr(patient_model, settings.LOG_PATIENT_FIELDNAME),
                    self.registry,
                    ex,
                )
            )

            raise RDRFContextSwitchError

    def _evaluate_form_rules(self, form_rules, evaluation_context):
        from rdrf.workflows.rules_engine import RulesEvaluator

        evaluator = RulesEvaluator(form_rules, evaluation_context)
        return evaluator.get_action()

    def _enable_context_creation_after_save(
        self, request, registry_code, form_id, patient_id
    ):
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

    @method_decorator(anonymous_not_allowed)
    @login_required_method
    def get(self, request, registry_code, form_id, patient_id, context_id=None):
        logger.info(
            "FORMGET %s %s %s %s %s"
            % (request.user, registry_code, form_id, patient_id, context_id)
        )
        # RDR-1398 enable a Create View which context_id of 'add' is provided
        if context_id is None:
            raise Http404
        self.CREATE_MODE = False  # Normal edit view; False means Create View and context saved AFTER validity check
        if context_id == "add":
            self._enable_context_creation_after_save(
                request, registry_code, form_id, patient_id
            )

        if request.user.is_working_group_staff:
            raise PermissionDenied()
        self.user = request.user
        self.form_id = form_id
        self.patient_id = patient_id

        try:
            patient_model = Patient.objects.get(pk=patient_id)
        except Patient.DoesNotExist:
            raise Http404

        security_check_user_patient(request.user, patient_model)

        self.registry = self._get_registry(registry_code)

        if self.registry.has_feature("consent_checks"):
            from rdrf.helpers.utils import consent_check

            if not consent_check(
                self.registry, self.user, patient_model, "see_patient"
            ):
                raise PermissionDenied

        custom_actions = [
            CustomActionWrapper(self.registry, self.user, custom_action, patient_model)
            for custom_action in self.user.get_custom_actions_by_scope(self.registry)
        ]

        self.rdrf_context_manager = RDRFContextManager(self.registry)

        try:
            if not self.CREATE_MODE:
                self.set_rdrf_context(patient_model, context_id)
        except RDRFContextSwitchError:
            return HttpResponseRedirect("/")

        if not self.CREATE_MODE:
            rdrf_context_id = self.rdrf_context.pk
            self.dynamic_data = self._get_dynamic_data(
                id=patient_id,
                registry_code=registry_code,
                rdrf_context_id=rdrf_context_id,
            )
        else:
            rdrf_context_id = "add"
            self.dynamic_data = None

        self.registry_form = self.get_registry_form(form_id)

        if not self.registry_form.applicable_to(patient_model):
            return HttpResponseRedirect(reverse("patientslisting"))

        context_launcher = RDRFContextLauncherComponent(
            request.user,
            self.registry,
            patient_model,
            self.registry_form.name,
            self.rdrf_context,
            registry_form=self.registry_form,
            rdrf_nonce=request.csp_nonce,
        )

        # Retrieve locking information
        if self.rdrf_context:
            try:
                clinical_data = ClinicalData.objects.get(
                    registry_code=self.registry.code,
                    collection="cdes",
                    django_id=patient_model.id,
                    django_model="Patient",
                    context_id=self.rdrf_context.id,
                )
                metadata_locking = clinical_data.get_metadata_locking(
                    self.registry_form.name
                )
            except ClinicalData.DoesNotExist:
                # The form has not been saved yet, so it is unlock.
                metadata_locking = False
        else:
            # Not context (for example clicking on add a FollowUp)
            metadata_locking = False

        context = self._build_context(
            user=request.user, patient_model=patient_model, rdrf_nonce=request.csp_nonce
        )
        context["location"] = location_name(self.registry_form, self.rdrf_context)
        # we provide a "path" to the header field which contains an embedded Django template
        context["header"] = self.registry_form.header
        context["header_expression"] = (
            "rdrf://model/RegistryForm/%s/header" % self.registry_form.pk
        )
        context["settings"] = settings
        context["registry_has_locking"] = self.registry.has_feature("form_locking")
        context["metadata_locking"] = metadata_locking
        context["can_lock"] = self.user and self.user.has_perm(
            "rdrf.form_%s_can_lock" % self.registry_form.name
        )
        patient_info_component = RDRFPatientInfoComponent(self.registry, patient_model)

        if not self.CREATE_MODE:
            context["CREATE_MODE"] = False
            context["show_print_button"] = True
            context["patient_info"] = patient_info_component.html
            context["show_archive_button"] = request.user.can_archive
            context["not_linked"] = not patient_model.is_linked
            context["archive_patient_url"] = (
                patient_model.get_archive_url(self.registry)
                if request.user.can_archive
                else ""
            )

        else:
            context["CREATE_MODE"] = True
            context["show_print_button"] = False
            context["show_archive_button"] = False

        wizard = NavigationWizard(
            self.user,
            self.registry,
            patient_model,
            NavigationFormType.CLINICAL,
            context_id,
            self.registry_form,
        )

        context["next_form_link"] = wizard.next_link
        context["context_id"] = context_id
        context["previous_form_link"] = wizard.previous_link
        context["context_launcher"] = context_launcher.html

        if request.user.is_parent:
            context["parent"] = ParentGuardian.objects.get(user=request.user)

        context["my_contexts_url"] = patient_model.get_contexts_url(self.registry)
        context["context_id"] = rdrf_context_id
        context["custom_actions"] = custom_actions
        return self._render_context(request, context)

    def _render_context(self, request, context):
        context.update(csrf(request))

        if context["metadata_locking"]:
            template = "rdrf_cdes/form_readonly.html"
        else:
            template = self._get_template()

        return render(request, template, context)

    def _get_field_ids(self, form_class):
        # the ids of each cde on the form
        return ",".join(form_class().fields.keys())

    @method_decorator(anonymous_not_allowed)
    @login_required_method
    def post(self, request, registry_code, form_id, patient_id, context_id=None):
        logger.info(
            "FORMPOST %s %s %s %s %s"
            % (request.user, registry_code, form_id, patient_id, context_id)
        )
        if context_id is None:
            raise Http404
        all_errors = []
        progress_dict = {}

        self.CREATE_MODE = False  # Normal edit view; False means Create View and context saved AFTER validity check
        sections_to_save = []  # when a section is validated it is added to this list
        all_sections_valid = True
        if context_id == "add":
            # The following switches on CREATE_MODE if conditions satisfied
            self._enable_context_creation_after_save(
                request, registry_code, form_id, patient_id
            )
        self._set_user(request, form_id)

        registry = Registry.objects.get(code=registry_code)
        self.registry = registry

        patient = Patient.objects.get(pk=patient_id)

        security_check_user_patient(request.user, patient)

        self.patient_id = patient_id

        self.rdrf_context_manager = RDRFContextManager(self.registry)

        try:
            if not self.CREATE_MODE:
                self.set_rdrf_context(patient, context_id)
        except RDRFContextSwitchError:
            return HttpResponseRedirect("/")

        if not self.CREATE_MODE:
            dyn_patient = DynamicDataWrapper(
                patient, rdrf_context_id=self.rdrf_context.pk
            )
        else:
            dyn_patient = DynamicDataWrapper(patient, rdrf_context_id="add")

        dyn_patient.user = request.user

        form_obj = self.get_registry_form(form_id)
        # this allows form level timestamps to be saved
        dyn_patient.current_form_model = form_obj
        self.registry_form = form_obj

        form_display_name = (
            form_obj.display_name if form_obj.display_name else form_obj.name
        )
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
                is_superuser=self.user.is_superuser,
                user_groups=self.user.groups.all(),
                patient_model=patient,
                csp_nonce=request.csp_nonce,
            )
            section_elements = section_model.get_elements()
            section_element_map[s] = section_elements
            section_field_ids_map[s] = self._get_field_ids(form_class)

            if not section_model.allow_multiple:
                all_sections_valid, error_count = self._add_form_sections(
                    form_class,
                    request,
                    s,
                    dyn_patient,
                    registry_code,
                    sections_to_save,
                    form_section,
                    error_count,
                    all_errors,
                )

            else:
                all_sections_valid, error_count = self._add_form_multi_sections(
                    section_model,
                    s,
                    formset_prefixes,
                    total_forms_ids,
                    initial_forms_ids,
                    form_class,
                    request,
                    dyn_patient,
                    registry_code,
                    sections_to_save,
                    form_section,
                    error_count,
                    all_errors,
                )

        if all_sections_valid:
            # Only save to the db iff all sections are valid
            # If all sections are valid, each section form instance  needs to be re-created here as other wise the links
            # to any upload files won't work
            # If any are invalid, nothing needs to be done as the forms have already been created from the form
            # submission data
            for section_info in sections_to_save:
                section_info.save()
                form_instance = section_info.recreate_form_instance()
                form_section[section_info.section_code] = form_instance

            clinical_data_saved_ok.send(
                sender=ClinicalData, patient=patient, saved_sections=sections_to_save
            )

            progress_dict = dyn_patient.save_form_progress(
                registry_code, context_model=self.rdrf_context
            )
            # Save one snapshot after all sections have being persisted
            dyn_patient.save_snapshot(
                registry_code,
                "cdes",
                form_name=form_obj.name,
                form_user=self.request.user.username,
            )

            # save report friendly field values
            try:
                if self.rdrf_context:
                    create_field_values(
                        registry,
                        patient,
                        self.rdrf_context,
                        remove_existing=True,
                        form_model=form_obj,
                    )
            except Exception as ex:
                logger.warning("error creating field values: %s" % ex)
                raise

            if self.CREATE_MODE and dyn_patient.rdrf_context_id != "add":
                # we've created the context on the fly so no redirect to the edit view on
                # the new context
                newly_created_context = RDRFContext.objects.get(
                    id=dyn_patient.rdrf_context_id
                )
                dyn_patient.save_form_progress(
                    registry_code, context_model=newly_created_context
                )

                try:
                    create_field_values(
                        registry,
                        patient,
                        newly_created_context,
                        remove_existing=True,
                        form_model=form_obj,
                    )
                # TODO: the following line is smelly - it is eating all exceptions.
                except Exception as ex:
                    logger.warning(
                        "Error creating field values for new context: %s" % ex
                    )

                return HttpResponseRedirect(
                    reverse(
                        "registry_form",
                        args=(
                            registry_code,
                            form_id,
                            patient.pk,
                            newly_created_context.pk,
                        ),
                    )
                )

            if dyn_patient.rdrf_context_id == "add":
                raise Exception("Content not created")

            if registry.has_feature("rulesengine"):
                rules_block = registry.metadata.get("rules", {})
                form_rules = rules_block.get(form_obj.name, [])
                if len(form_rules) > 0:
                    # this may redirect or produce side effects
                    rules_evaluation_context = {
                        "patient_model": patient,
                        "registry_model": registry,
                        "form_name": form_obj.name,
                        "context_id": self.rdrf_context.pk,
                        "clinical_data": None,
                    }
                    action_result = self._evaluate_form_rules(
                        form_rules, rules_evaluation_context
                    )
                    if isinstance(action_result, HttpResponseRedirect):
                        return action_result

        patient_name = "%s %s" % (patient.given_names, patient.family_name)
        # progress saved to progress collection in mongo
        # the data is returned also
        wizard = NavigationWizard(
            self.user,
            registry,
            patient,
            NavigationFormType.CLINICAL,
            context_id,
            form_obj,
        )

        context_launcher = RDRFContextLauncherComponent(
            request.user,
            registry,
            patient,
            self.registry_form.name,
            self.rdrf_context,
            registry_form=self.registry_form,
            rdrf_nonce=request.csp_nonce,
        )

        patient_info_component = RDRFPatientInfoComponent(registry, patient)

        custom_actions = [
            CustomActionWrapper(registry, request.user, custom_action, patient)
            for custom_action in request.user.get_custom_actions_by_scope(registry)
        ]

        context = {
            "CREATE_MODE": self.CREATE_MODE,
            "current_registry_name": registry.name,
            "current_form_name": form_obj.display_name
            if form_obj.display_name
            else de_camelcase(form_obj.name),
            "registry": registry_code,
            "registry_code": registry_code,
            "form_name": form_id,
            "form_display_name": form_display_name,
            "patient_id": patient_id,
            "patient_link": PatientLocator(registry, patient).link,
            "patient": patient,
            "sections": sections,
            "patient_info": patient_info_component.html,
            "section_field_ids_map": section_field_ids_map,
            "section_ids": ids,
            "forms": form_section,
            "my_contexts_url": patient.get_contexts_url(self.registry),
            "display_names": display_names,
            "section_element_map": section_element_map,
            "total_forms_ids": total_forms_ids,
            "initial_forms_ids": initial_forms_ids,
            "formset_prefixes": formset_prefixes,
            "form_links": self._get_formlinks(request.user, self.rdrf_context),
            "metadata_json_for_sections": self._get_metadata_json_dict(
                self.registry_form
            ),
            "has_form_progress": self.registry_form.has_progress_indicator,
            "location": location_name(self.registry_form, self.rdrf_context),
            "next_form_link": wizard.next_link,
            "not_linked": not patient.is_linked,
            "previous_form_link": wizard.previous_link,
            "context_id": context_id,
            "show_print_button": True if not self.CREATE_MODE else False,
            "archive_patient_url": patient.get_archive_url(registry)
            if request.user.can_archive
            else "",
            "show_archive_button": request.user.can_archive
            if not self.CREATE_MODE
            else False,
            "context_launcher": context_launcher.html,
            "have_dynamic_data": all_sections_valid,
            "settings": settings,
            "custom_actions": custom_actions,
        }

        if request.user.is_parent:
            context["parent"] = ParentGuardian.objects.get(user=request.user)

        if not self.registry_form.is_questionnaire:
            form_progress_map = progress_dict.get(
                self.registry_form.name + "_form_progress", {}
            )
            if "percentage" in form_progress_map:
                progress_percentage = form_progress_map["percentage"]
            else:
                progress_percentage = 0

            context["form_progress"] = progress_percentage
            initial_completion_cdes = {
                cde_model.name: False
                for cde_model in self.registry_form.complete_form_cdes.all()
            }

            context["form_progress_cdes"] = progress_dict.get(
                self.registry_form.name + "_form_cdes_status", initial_completion_cdes
            )

        context.update(csrf(request))
        self.registry_form = self.get_registry_form(form_id)

        context["header"] = self.registry_form.header
        context["header_expression"] = (
            "rdrf://model/RegistryForm/%s/header" % self.registry_form.pk
        )

        if error_count == 0:
            success_message = _(
                "Patient %(patient_name)s saved successfully. Please now use the blue arrow on the right to continue."
            ) % {"patient_name": patient_name}
            messages.add_message(request, messages.SUCCESS, success_message)
        else:
            failure_message = _(
                "Patient %(patient_name)s not saved due to validation errors"
            ) % {"patient_name": patient_name}

            messages.add_message(request, messages.ERROR, failure_message)

        return render(request, self._get_template(), context)

    def _set_user(self, request, form_id):
        if request.user.is_superuser:
            pass
        elif request.user.is_working_group_staff or request.user.has_perm(
            "rdrf.form_%s_is_readonly" % form_id
        ):
            raise PermissionDenied()

        self.user = request.user

    def _add_form_multi_sections(
        self,
        section_model,
        section_code,
        formset_prefixes,
        total_forms_ids,
        initial_forms_ids,
        form_class,
        request,
        dyn_patient,
        registry_code,
        sections_to_save,
        form_section,
        error_count,
        all_errors,
    ):
        all_sections_valid = True
        if section_model.extra:
            extra = section_model.extra
        else:
            extra = 0

        prefix = "formset_%s" % section_code
        formset_prefixes[section_code] = prefix
        total_forms_ids[section_code] = "id_%s-TOTAL_FORMS" % prefix
        initial_forms_ids[section_code] = "id_%s-INITIAL_FORMS" % prefix
        form_set_class = formset_factory(form_class, extra=extra, can_delete=True)
        formset = form_set_class(request.POST, files=request.FILES, prefix=prefix)
        assert formset.prefix == prefix

        if formset.is_valid():
            dynamic_data = formset.cleaned_data  # a list of values
            to_remove = [i for i, d in enumerate(dynamic_data) if d.get("DELETE")]
            index_map = make_index_map(to_remove, len(dynamic_data))

            for i in reversed(to_remove):
                del dynamic_data[i]

            current_data = dyn_patient.load_dynamic_data(self.registry.code, "cdes")
            section_dict = {section_code: dynamic_data}
            section_info = SectionInfo(
                section_code,
                dyn_patient,
                True,
                registry_code,
                "cdes",
                section_dict,
                index_map,
                form_set_class=form_set_class,
                prefix=prefix,
            )

            sections_to_save.append(section_info)
            form_data = wrap_file_cdes(
                registry_code,
                dynamic_data,
                current_data,
                multisection=True,
                index_map=index_map,
            )
            form_section[section_code] = form_set_class(
                initial=form_data, prefix=prefix
            )

        else:
            all_sections_valid = False
            for e in formset.errors:
                error_count += 1
                all_errors.append(e)
            form_section[section_code] = form_set_class(
                request.POST, request.FILES, prefix=prefix
            )
        return all_sections_valid, error_count

    def _add_form_sections(
        self,
        form_class,
        request,
        section_code,
        dyn_patient,
        registry_code,
        sections_to_save,
        form_section,
        error_count,
        all_errors,
    ):
        all_sections_valid = True
        form = form_class(request.POST, files=request.FILES)
        if form.is_valid():
            dynamic_data = form.cleaned_data
            section_info = SectionInfo(
                section_code,
                dyn_patient,
                False,
                registry_code,
                "cdes",
                dynamic_data,
                form_class=form_class,
            )
            sections_to_save.append(section_info)
            current_data = dyn_patient.load_dynamic_data(self.registry.code, "cdes")
            form_data = wrap_file_cdes(
                registry_code, dynamic_data, current_data, multisection=False
            )
            form_section[section_code] = form_class(dynamic_data, initial=form_data)
        else:
            all_sections_valid = False
            for e in form.errors:
                error_count += 1
                all_errors.append(e)

            from rdrf.helpers.utils import wrap_uploaded_files

            post_copy = request.POST.copy()
            # request.POST.update(request.FILES)
            post_copy.update(request.FILES)

            form_section[section_code] = form_class(
                wrap_uploaded_files(registry_code, post_copy), request.FILES
            )
        return all_sections_valid, error_count

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

    def _get_form_class_for_section(
        self, registry, registry_form, section, rdrf_nonce=None
    ):
        return create_form_class_for_section(
            registry,
            registry_form,
            section,
            injected_model="Patient",
            injected_model_id=self.patient_id,
            is_superuser=self.request.user.is_superuser,
            user_groups=self.request.user.groups.all(),
            csp_nonce=rdrf_nonce,
        )

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
                    selected=(form.name == self.registry_form.name),
                    context_model=self.rdrf_context,
                )
                for form in container_model.forms
                if not form.is_questionnaire and user.can_view(form)
            ]
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
        rdrf_nonce = kwargs.get("rdrf_nonce", None)
        if self.dynamic_data:
            if "questionnaire_context" in kwargs:
                self.dynamic_data["questionnaire_context"] = kwargs[
                    "questionnaire_context"
                ]
            else:
                self.dynamic_data["questionnaire_context"] = "au"

        for s in sections:
            section_model = Section.objects.get(code=s)
            form_class = self._get_form_class_for_section(
                self.registry, self.registry_form, section_model, rdrf_nonce
            )
            section_elements = section_model.get_elements()
            section_element_map[s] = section_elements
            section_field_ids_map[s] = self._get_field_ids(form_class)

            if not section_model.allow_multiple:
                # return a normal form
                initial_data = wrap_fs_data_for_form(self.registry, self.dynamic_data)
                form_section[s] = form_class(self.dynamic_data, initial=initial_data)
                if self.registry.has_feature("verification"):
                    annotate_form_with_verifications(
                        patient_model,
                        self.rdrf_context,
                        self.registry,
                        self.registry_form,
                        section_model,
                        initial_data,
                        form_section[s],
                    )

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
                form_set_class = formset_factory(
                    form_class,
                    extra=extra,
                    can_delete=self.show_multisection_delete_checkbox,
                )
                if self.dynamic_data:
                    try:
                        # we grab the list of data items by section code not cde code
                        initial_data = wrap_fs_data_for_form(
                            self.registry, self.dynamic_data[s]
                        )
                    except KeyError:
                        initial_data = [""]  # * len(section_elements)
                else:
                    # initial_data = [""] * len(section_elements)
                    initial_data = [""]  # this appears to forms

                form_section[s] = form_set_class(initial=initial_data, prefix=prefix)

        context = {
            "CREATE_MODE": self.CREATE_MODE,
            "old_style_demographics": self.registry.code != "fkrp",
            "current_registry_name": self.registry.name,
            "current_form_name": self.registry_form.display_name
            if self.registry_form.display_name
            else de_camelcase(self.registry_form.name),
            "registry": self.registry.code,
            "registry_code": self.registry.code,
            "form_name": self.form_id,
            "form_display_name": self.registry_form.name,
            "patient_id": self._get_patient_id(),
            "patient_link": PatientLocator(self.registry, patient_model).link,
            "patient": patient_model,
            "patient_name": self._get_patient_name(),
            "sections": sections,
            "forms": form_section,
            "display_names": display_names,
            "section_ids": ids,
            "not_linked": patient_model.is_linked if patient_model else True,
            "section_element_map": section_element_map,
            "total_forms_ids": total_forms_ids,
            "section_field_ids_map": section_field_ids_map,
            "initial_forms_ids": initial_forms_ids,
            "formset_prefixes": formset_prefixes,
            "form_links": form_links,
            "metadata_json_for_sections": self._get_metadata_json_dict(
                self.registry_form
            ),
            "has_form_progress": self.registry_form.has_progress_indicator,
            "have_dynamic_data": bool(self.dynamic_data),
            "settings": settings,
        }

        if (
            not self.registry_form.is_questionnaire
            and self.registry_form.has_progress_indicator
        ):

            form_progress = FormProgress(self.registry_form.registry)

            form_progress_percentage = form_progress.get_form_progress(
                self.registry_form, patient_model, self.rdrf_context
            )

            form_cdes_status = form_progress.get_form_cdes_status(
                self.registry_form, patient_model, self.rdrf_context
            )

            context["form_progress"] = form_progress_percentage
            context["form_progress_cdes"] = form_cdes_status

        context.update(kwargs)
        return context

    def _get_patient_id(self):
        return self.patient_id

    def _get_patient_name(self):
        patient = Patient.objects.get(pk=self.patient_id)
        patient_name = "%s %s" % (patient.given_names, patient.family_name)
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
        from rdrf.helpers.utils import id_on_page

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
                            metadata[cde_code_on_page]["row_selector"] = (
                                cde_code_on_page + "_month"
                            )

            if metadata:
                json_dict[section] = json.dumps(metadata)

        return json_dict

    # fixme: could replace with TemplateView.get_template_names()
    def _get_template(self):
        if (
            self.user
            and self.user.has_perm("rdrf.form_%s_is_readonly" % self.form_id)
            and not self.user.is_superuser
        ):
            return "rdrf_cdes/form_readonly.html"

        return "rdrf_cdes/form.html"


class FormPrintView(FormView):
    def _get_template(self):
        return "rdrf_cdes/form_print.html"


class FormFieldHistoryView(TemplateView):
    template_name = "rdrf_cdes/form_field_history.html"

    @method_decorator(anonymous_not_allowed)
    @login_required_method
    def get(self, request, **kwargs):
        if request.user.is_working_group_staff:
            raise PermissionDenied()
        return super(FormFieldHistoryView, self).get(request, **kwargs)

    def get_context_data(
        self, registry_code, form_id, patient_id, context_id, section_code, cde_code
    ):
        context = super(FormFieldHistoryView, self).get_context_data()

        # find database objects from url route params
        reg = get_object_or_404(Registry, code=registry_code)
        reg_form = get_object_or_404(RegistryForm, registry=reg, pk=form_id)
        cde = get_object_or_404(CommonDataElement, code=cde_code)
        patient = get_object_or_404(Patient, pk=patient_id)
        rdrf_context = get_object_or_404(RDRFContext, registry=reg, pk=context_id)

        # grab snapshot values out of mongo documents
        dyn_patient = DynamicDataWrapper(patient, rdrf_context_id=rdrf_context.id)
        val = dyn_patient.get_cde_val(
            registry_code, reg_form.name, section_code, cde_code
        )
        history = dyn_patient.get_cde_history(
            registry_code, reg_form.name, section_code, cde_code
        )

        context.update(
            {
                "cde": cde,
                "value": val,
                "history": history,
            }
        )
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
        self.template = "rdrf_cdes/questionnaire.html"
        self.CREATE_MODE = False
        self.show_multisection_delete_checkbox = False

    @method_decorator(patient_questionnaire_access)
    def get(self, request, registry_code, questionnaire_context="au"):
        try:
            if questionnaire_context is not None:
                self.questionnaire_context = questionnaire_context
            else:
                self.questionnaire_context = "au"
            self.registry = self._get_registry(registry_code)
            form = self.registry.questionnaire
            if form is None:
                raise RegistryForm.DoesNotExist()

            self.registry_form = form
            context = self._build_context(
                questionnaire_context=questionnaire_context,
                rdrf_nonce=request.csp_nonce,
            )

            custom_consent_helper = CustomConsentHelper(self.registry)
            custom_consent_helper.create_custom_consent_wrappers()

            context["custom_consent_errors"] = {}
            context[
                "custom_consent_wrappers"
            ] = custom_consent_helper.custom_consent_wrappers
            context["registry"] = self.registry
            context["country_code"] = questionnaire_context
            context["prelude_file"] = self._get_prelude(
                registry_code, questionnaire_context
            )
            context["show_print_button"] = False

            return self._render_context(request, context)
        except RegistryForm.DoesNotExist:
            context = {
                "registry": self.registry,
                "error_msg": "No questionnaire for registry %s" % registry_code,
            }
        except RegistryForm.MultipleObjectsReturned:
            context = {
                "registry": self.registry,
                "error_msg": "Multiple questionnaire exists for %s" % registry_code,
            }
        return render(request, "rdrf_cdes/questionnaire_error.html", context)

    def _get_template(self):
        return "rdrf_cdes/questionnaire.html"

    def _get_prelude(self, registry_code, questionnaire_context):
        if questionnaire_context is None:
            prelude_file = "prelude_%s.html" % registry_code
        else:
            prelude_file = "prelude_%s_%s.html" % (registry_code, questionnaire_context)

        file_path = os.path.join(
            settings.TEMPLATES[0]["DIRS"][0], "rdrf_cdes", prelude_file
        )
        if os.path.exists(file_path):
            return os.path.join("rdrf_cdes", prelude_file)
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
                self.registry, consent_section_model
            )
            consent_form = consent_form_class(data=post_data)
            consent_form_wrapper = ConsentFormWrapper(
                consent_section_model.section_label, consent_form, consent_section_model
            )
            consent_form_wrappers.append(consent_form_wrapper)

        return consent_form_wrappers

    @method_decorator(patient_questionnaire_access)
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
            section_model = Section.objects.get(code=section)
            section_elements = section_model.get_elements()
            section_element_map[section] = section_elements
            form_class = create_form_class_for_section(
                registry,
                questionnaire_form,
                section_model,
                questionnaire_context=self.questionnaire_context,
                csp_nonce=request.csp_nonce,
            )
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

                prefix = "formset_%s" % section
                form_set_class = formset_factory(
                    form_class, extra=extra, can_delete=True
                )
                form_section[section] = form_set_class(
                    request.POST, request.FILES, prefix=prefix
                )
                formset_prefixes[section] = prefix
                total_forms_ids[section] = "id_%s-TOTAL_FORMS" % prefix
                initial_forms_ids[section] = "id_%s-INITIAL_FORMS" % prefix
                formset = form_set_class(request.POST, prefix=prefix)

                if formset.is_valid():
                    dynamic_data = formset.cleaned_data  # a list of values
                    section_dict = {}
                    section_dict[section] = dynamic_data
                    data_map[section] = section_dict
                else:
                    for e in formset.errors:
                        error_count += 1

        if error_count == 0:
            questionnaire_response = QuestionnaireResponse()
            questionnaire_response.registry = registry
            questionnaire_response.save()
            questionnaire_response_wrapper = DynamicDataWrapper(questionnaire_response)
            questionnaire_response_wrapper.current_form_model = questionnaire_form
            questionnaire_response_wrapper.save_dynamic_data(
                registry_code,
                "cdes",
                {"custom_consent_data": custom_consent_helper.custom_consent_data},
            )

            for section in sections:
                data_map[section]["questionnaire_context"] = self.questionnaire_context
                if is_multisection(section):
                    questionnaire_response_wrapper.save_dynamic_data(
                        registry_code,
                        "cdes",
                        data_map[section],
                        multisection=True,
                        additional_data={
                            "questionnaire_context": self.questionnaire_context
                        },
                    )
                else:
                    questionnaire_response_wrapper.save_dynamic_data(
                        registry_code,
                        "cdes",
                        data_map[section],
                        additional_data={
                            "questionnaire_context": self.questionnaire_context
                        },
                    )

            def get_completed_questions(
                questionnaire_form_model,
                data_map,
                custom_consent_data,
                consent_wrappers,
            ):
                section_map = OrderedDict()

                class SectionWrapper(object):
                    def __init__(self, label):
                        self.label = label
                        self.is_multi = False
                        self.subsections = []
                        self.questions = []

                    def load_consents(self, consent_section_model, custom_consent_data):
                        for (
                            consent_question_model
                        ) in consent_section_model.questions.order_by("position"):
                            question_wrapper = ConsentQuestionWrapper()
                            question_wrapper.label = consent_question_model.label(
                                on_questionnaire=True
                            )
                            field_key = consent_question_model.field_key
                            try:
                                value = custom_consent_data[field_key]
                                if value == "on":
                                    question_wrapper.answer = "Yes"
                            except KeyError:
                                pass
                            self.questions.append(question_wrapper)

                class Question(object):
                    def __init__(self, delimited_key, value):
                        self.delimited_key = delimited_key  # in Mongo
                        self.value = value  # value in Mongo
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
                            elif cde_model.datatype == "boolean":
                                if self.value:
                                    return "Yes"
                                else:
                                    return "No"
                            elif cde_model.datatype == "date":
                                return parse_iso_date(self.value).strftime("%d-%m-%Y")
                            return str(self.value)

                    def _get_cde_model(self):
                        _, _, cde_code = self.delimited_key.split("____")
                        return CommonDataElement.objects.get(code=cde_code)

                def get_question(form_model, section_model, cde_model, data_map):
                    from rdrf.helpers.utils import mongo_key_from_models

                    delimited_key = mongo_key_from_models(
                        form_model, section_model, cde_model
                    )
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
                        consent_section_model, custom_consent_helper.custom_consent_data
                    )
                    section_map[sw.label] = sw

                for section_model in questionnaire_form_model.section_models:
                    section_label = (
                        section_model.questionnaire_display_name
                        or section_model.display_name
                    )
                    if section_label not in section_map:
                        section_map[section_label] = SectionWrapper(section_label)
                    if not section_model.allow_multiple:

                        for cde_model in section_model.cde_models:
                            question = get_question(
                                questionnaire_form_model,
                                section_model,
                                cde_model,
                                data_map,
                            )
                            section_map[section_label].questions.append(question)
                    else:
                        section_map[section_label].is_multi = True

                        for multisection_map in data_map[section_model.code][
                            section_model.code
                        ]:
                            subsection = []
                            section_wrapper = {section_model.code: multisection_map}
                            for cde_model in section_model.cde_models:
                                question = get_question(
                                    questionnaire_form_model,
                                    section_model,
                                    cde_model,
                                    section_wrapper,
                                )
                                subsection.append(question)
                            section_map[section_label].subsections.append(subsection)

                return section_map

            section_map = get_completed_questions(
                questionnaire_form,
                data_map,
                custom_consent_helper.custom_consent_data,
                custom_consent_helper.custom_consent_wrappers,
            )

            context = {}
            context["custom_consent_errors"] = {}
            context["completed_sections"] = section_map
            context["prelude"] = self._get_prelude(
                registry_code, self.questionnaire_context
            )

            return render(
                request, "rdrf_cdes/completed_questionnaire_thankyou.html", context
            )
        else:
            context = {
                "custom_consent_wrappers": custom_consent_helper.custom_consent_wrappers,
                "custom_consent_errors": custom_consent_helper.custom_consent_errors,
                "registry": registry_code,
                "form_name": "questionnaire",
                "form_display_name": registry.questionnaire.name,
                "patient_id": "dummy",
                "patient_name": "",
                "sections": sections,
                "forms": form_section,
                "display_names": display_names,
                "section_element_map": section_element_map,
                "section_field_ids_map": section_field_ids_map,
                "total_forms_ids": total_forms_ids,
                "initial_forms_ids": initial_forms_ids,
                "formset_prefixes": formset_prefixes,
                "metadata_json_for_sections": self._get_metadata_json_dict(
                    self.registry_form
                ),
            }

            context.update(csrf(request))
            messages.add_message(
                request,
                messages.ERROR,
                _(
                    "The questionnaire was not submitted because of validation errors - please try again"
                ),
            )
            return render(request, "rdrf_cdes/questionnaire.html", context)

    def _get_patient_id(self):
        return "questionnaire"

    def _get_patient_name(self):
        return "questionnaire"

    def _get_form_class_for_section(
        self, registry, registry_form, section, rdrf_nonce=None
    ):
        return create_form_class_for_section(
            registry,
            registry_form,
            section,
            questionnaire_context=self.questionnaire_context,
            csp_nonce=rdrf_nonce,
        )


class QuestionnaireHandlingView(View):
    @method_decorator(anonymous_not_allowed)
    @method_decorator(login_required)
    def get(self, request, registry_code, questionnaire_response_id):
        from rdrf.workflows.questionnaires.questionnaires import Questionnaire

        context = csrf(request)
        template_name = "rdrf_cdes/questionnaire_handling.html"
        context["registry_model"] = get_object_or_404(Registry, code=registry_code)
        context["form_model"] = context["registry_model"].questionnaire
        context["qr_model"] = get_object_or_404(
            QuestionnaireResponse, id=questionnaire_response_id
        )
        context["patient_lookup_url"] = reverse("patient_lookup", args=(registry_code,))

        context["questionnaire"] = Questionnaire(
            context["registry_model"], context["qr_model"]
        )

        return render(request, template_name, context)


class FileUploadView(View):
    @method_decorator(anonymous_not_allowed)
    @login_required_method
    def get(self, request, registry_code, file_id):
        data, filename = filestorage.get_file(file_id)
        if data is not None:
            response = FileResponse(data, content_type="application/octet-stream")
            response["Content-disposition"] = 'filename="%s"' % filename
        else:
            response = HttpResponseNotFound()
        return response


class StandardView(object):
    TEMPLATE_DIR = "rdrf_cdes"
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

    @method_decorator(anonymous_not_allowed)
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
                    self.section_model.code, self.cde_model.code
                ):
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
                lst = []
                for cde_model in self.section_model.cde_models:
                    lst.append(
                        QuestionWrapper(
                            self.registry_form, self.section_model, cde_model
                        )
                    )
                return lst

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


class RPCHandler(View):
    @method_decorator(anonymous_not_allowed)
    @method_decorator(login_required)
    def post(self, request):
        action_dict = json.loads(request.body.decode("utf-8"))
        action_executor = ActionExecutor(request, action_dict)
        client_response_dict = action_executor.run()
        client_response_json = json.dumps(client_response_dict)
        return HttpResponse(
            client_response_json, status=200, content_type="application/json"
        )


class Colours(object):
    grey = "#808080"
    blue = "#0000ff"
    green = "#00ff00"
    red = "#f7464a"
    yellow = "#ffff00"


class CustomConsentFormView(View):
    @method_decorator(anonymous_not_allowed)
    @method_decorator(login_required)
    def get(self, request, registry_code, patient_id, context_id=None):
        logger.info(
            "CONSENTGET %s %s %s %s"
            % (request.user, registry_code, patient_id, context_id)
        )
        if not request.user.is_authenticated:
            consent_form_url = reverse(
                "consent_form_view", args=[registry_code, patient_id]
            )
            login_url = reverse("two_factor:login")
            return redirect("%s?next=%s" % (login_url, consent_form_url))

        patient_model = Patient.objects.get(pk=patient_id)

        security_check_user_patient(request.user, patient_model)

        registry_model = Registry.objects.get(code=registry_code)
        form_sections = self._get_form_sections(registry_model, patient_model)
        wizard = NavigationWizard(
            request.user,
            registry_model,
            patient_model,
            NavigationFormType.CONSENTS,
            context_id,
            None,
        )

        try:
            parent = ParentGuardian.objects.get(user=request.user)
        except ParentGuardian.DoesNotExist:
            parent = None

        context_launcher = RDRFContextLauncherComponent(
            request.user,
            registry_model,
            patient_model,
            current_form_name="Consents",
            rdrf_nonce=request.csp_nonce,
        )

        patient_info = RDRFPatientInfoComponent(registry_model, patient_model)

        custom_actions = [
            CustomActionWrapper(
                registry_model, request.user, custom_action, patient_model
            )
            for custom_action in request.user.get_custom_actions_by_scope(
                registry_model
            )
        ]

        context = {
            "location": "Consents",
            "forms": form_sections,
            "context_id": context_id,
            "show_archive_button": request.user.can_archive,
            "not_linked": not patient_model.is_linked,
            "archive_patient_url": patient_model.get_archive_url(registry_model)
            if request.user.can_archive
            else "",
            "form_name": "fixme",  # required for form_print link
            "patient": patient_model,
            "patient_id": patient_model.id,
            "registry_code": registry_code,
            "patient_link": PatientLocator(registry_model, patient_model).link,
            "context_launcher": context_launcher.html,
            "patient_info": patient_info.html,
            "next_form_link": wizard.next_link,
            "previous_form_link": wizard.previous_link,
            "parent": parent,
            "consent": consent_status_for_patient(registry_code, patient_model),
            "show_print_button": True,
            "custom_actions": custom_actions,
        }

        return render(request, "rdrf_cdes/custom_consent_form.html", context)

    def _get_initial_consent_data(self, patient_model):
        # load initial consent data for custom consent form
        if patient_model is None:
            return {}
        initial_data = {}
        data = patient_model.consent_questions_data
        for consent_field_key in data:
            initial_data[consent_field_key] = data[consent_field_key]
        return initial_data

    def _get_form_sections(self, registry_model, patient_model):
        custom_consent_form_generator = CustomConsentFormGenerator(
            registry_model, patient_model
        )
        initial_data = self._get_initial_consent_data(patient_model)
        custom_consent_form = custom_consent_form_generator.create_form(initial_data)

        patient_consent_file_forms = self._get_consent_file_formset(patient_model)

        consent_sections = custom_consent_form.get_consent_sections()

        patient_section_consent_file = (_("Upload consent file (if requested)"), None)

        return self._section_structure(
            custom_consent_form,
            consent_sections,
            patient_consent_file_forms,
            patient_section_consent_file,
        )

    def _get_consent_file_formset(self, patient_model):
        patient_consent_file_formset = inlineformset_factory(
            Patient,
            PatientConsent,
            form=PatientConsentFileForm,
            extra=0,
            can_delete=True,
            fields="__all__",
        )

        patient_consent_file_forms = patient_consent_file_formset(
            instance=patient_model, prefix="patient_consent_file"
        )
        return patient_consent_file_forms

    def _section_structure(
        self,
        custom_consent_form,
        consent_sections,
        patient_consent_file_forms,
        patient_section_consent_file,
    ):
        return [
            (
                custom_consent_form,
                consent_sections,
            ),
            (patient_consent_file_forms, (patient_section_consent_file,)),
        ]

    def _get_success_url(self, registry_model, patient_model):
        return reverse(
            "consent_form_view", args=[registry_model.code, patient_model.pk]
        )

    @method_decorator(anonymous_not_allowed)
    @method_decorator(login_required)
    def post(self, request, registry_code, patient_id, context_id=None):
        logger.info(
            "CONSENTPOST %s %s %s %s"
            % (request.user, registry_code, patient_id, context_id)
        )
        if not request.user.is_authenticated:
            consent_form_url = reverse(
                "consent_form_view", args=[registry_code, patient_id, context_id]
            )
            login_url = reverse("two_factor:login")
            return redirect("%s?next=%s" % (login_url, consent_form_url))

        registry_model = Registry.objects.get(code=registry_code)
        patient_model = Patient.objects.get(id=patient_id)

        security_check_user_patient(request.user, patient_model)

        context_launcher = RDRFContextLauncherComponent(
            request.user,
            registry_model,
            patient_model,
            current_form_name="Consents",
            rdrf_nonce=request.csp_nonce,
        )

        wizard = NavigationWizard(
            request.user,
            registry_model,
            patient_model,
            NavigationFormType.CONSENTS,
            context_id,
            None,
        )

        patient_consent_file_formset = inlineformset_factory(
            Patient, PatientConsent, form=PatientConsentFileForm, fields="__all__"
        )

        patient_consent_file_forms = patient_consent_file_formset(
            request.POST,
            request.FILES,
            instance=patient_model,
            prefix="patient_consent_file",
        )
        patient_section_consent_file = (_("Upload consent file (if requested)"), None)

        custom_consent_form_generator = CustomConsentFormGenerator(
            registry_model, patient_model
        )
        custom_consent_form = custom_consent_form_generator.create_form(request.POST)
        consent_sections = custom_consent_form.get_consent_sections()

        forms_to_validate = [custom_consent_form, patient_consent_file_forms]

        form_sections = self._section_structure(
            custom_consent_form,
            consent_sections,
            patient_consent_file_forms,
            patient_section_consent_file,
        )
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

        if all(valid_forms):
            patient_consent_file_forms.save()
            custom_consent_form.save()
            patient_name = "%s %s" % (
                patient_model.given_names,
                patient_model.family_name,
            )
            messages.success(
                self.request,
                _(
                    "Patient %(patient_name)s saved successfully. Please now use the blue arrow on the right to continue."
                )
                % {"patient_name": patient_name},
            )
            return HttpResponseRedirect(
                self._get_success_url(registry_model, patient_model)
            )
        else:
            try:
                parent = ParentGuardian.objects.get(user=request.user)
            except ParentGuardian.DoesNotExist:
                parent = None

            context = {
                "location": "Consents",
                "patient": patient_model,
                "patient_id": patient_model.id,
                "patient_link": PatientLocator(registry_model, patient_model).link,
                "context_id": context_id,
                "registry_code": registry_code,
                "show_archive_button": request.user.can_archive,
                "not_linked": not patient_model.is_linked,
                "archive_patient_url": patient_model.get_archive_url(registry_model)
                if request.user.can_archive
                else "",
                "next_form_link": wizard.next_link,
                "previous_form_link": wizard.previous_link,
                "context_launcher": context_launcher.html,
                "forms": form_sections,
                "error_messages": [],
                "parent": parent,
                "consent": consent_status_for_patient(registry_code, patient_model),
            }

            context["message"] = _("Consent section not complete")
            context["error_messages"] = error_messages
            context["errors"] = True

            return render(request, "rdrf_cdes/custom_consent_form.html", context)
