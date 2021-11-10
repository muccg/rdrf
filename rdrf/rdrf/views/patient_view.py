from collections import OrderedDict

from django.shortcuts import render, redirect
from django.views.generic.base import View
from django.views.generic import CreateView
from django.urls import reverse
from django.http import HttpResponseRedirect, Http404

from rdrf.models.definition.models import Registry
from rdrf.models.definition.models import CdePolicy
from rdrf.helpers.utils import consent_status_for_patient
from rdrf.helpers.utils import anonymous_not_allowed

from django.forms.models import inlineformset_factory
from django.utils.html import strip_tags

from registry.patients.models import ParentGuardian
from registry.patients.models import Patient
from registry.patients.models import PatientAddress
from registry.patients.models import PatientDoctor
from registry.patients.models import PatientRelative
from registry.patients.admin_forms import PatientAddressForm
from registry.patients.admin_forms import PatientDoctorForm
from registry.patients.admin_forms import PatientForm
# from registry.patients.admin_forms import get_patient_form_class_with_external_fields

from registry.patients.admin_forms import PatientRelativeForm
from django.utils.translation import ugettext as _

from rdrf.forms.dynamic.registry_specific_fields import RegistrySpecificFieldsHandler
from rdrf.helpers.utils import get_error_messages
from rdrf.forms.navigation.wizard import NavigationWizard, NavigationFormType
from rdrf.forms.components import RDRFContextLauncherComponent
from rdrf.forms.components import RDRFPatientInfoComponent
from rdrf.forms.components import FamilyLinkagePanel
from rdrf.db.contexts_api import RDRFContextManager
from rdrf.views.custom_actions import CustomActionWrapper

from rdrf.security.security_checks import security_check_user_patient
from django.core.exceptions import PermissionDenied
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required


import logging
logger = logging.getLogger(__name__)


def get_external_patient_fields():
    from intframework.models import HL7Mapping
    fields = []
    for mapping in HL7Mapping.objects.all():
        event_map = mapping.load()
        for key in event_map:
            if key.startswith("Demographics/"):
                _, field = key.split("/")
                fields.append(field)
    return fields


class PatientMixin(object):
    model = Patient

    def get_context_data(self, **kwargs):
        kwargs.update({'object_name': 'Patient'})
        return kwargs


class PatientFormMixin(PatientMixin):
    original_form_class = PatientForm
    template_name = 'rdrf_cdes/generic_patient.html'

    def __init__(self, *args, **kwargs):
        super(PatientFormMixin, self).__init__(*args, **kwargs)
        self.user = None   # filled in via get or post
        self.registry_model = None
        self.patient_form = None  # created via get_form
        self.patient_model = None
        self.address_formset = None
        self.doctor_formset = None
        self.patient_relative_formset = None
        self.object = None
        self.patient_consent_file_formset = None
        self.request = None   # set in post so RegistrySpecificFieldsHandler can process files

    # common methods

    def load_custom_actions(self):
        if self.user and self.patient_model and self.registry_model:
            return [CustomActionWrapper(self.registry_model,
                                        self.user,
                                        custom_action,
                                        self.patient_model) for custom_action in
                    self.user.custom_actions(self.registry_model)]
        else:
            return []

    def _get_registry_specific_fields(self, user, registry_model):
        """
        :param user:
        :param registry_model:
        :return: list of cde_model, field_object pairs
        """
        if user.is_superuser:
            return registry_model.patient_fields

        if registry_model not in user.registry.all():
            return []
        else:
            return registry_model.patient_fields

    def get_form_class(self):
        if not self.registry_model.patient_fields:
            return self.original_form_class

        form_class = self._create_registry_specific_patient_form_class(self.user,
                                                                       self.original_form_class,
                                                                       self.registry_model)
        return form_class

    def _set_registry_model(self, registry_code):
        self.registry_model = Registry.objects.get(code=registry_code)

    def get_success_url(self):
        """
        After a successful add where to go?
        Returns the supplied success URL. (We override to redirect to edit screen for the newly added patient)
        """
        registry_code = self.registry_model.code
        patient_id = self.object.pk
        patient_edit_url = reverse('patient_edit', args=[registry_code, patient_id])
        return '%s?just_created=True' % patient_edit_url

    def _get_initial_context(self, registry_code, patient_model):
        from rdrf.models.definition.models import Registry
        registry_model = Registry.objects.get(code=registry_code)
        rdrf_context_manager = RDRFContextManager(registry_model)
        return rdrf_context_manager.get_or_create_default_context(
            patient_model, new_patient=True)

    def set_patient_model(self, patient_model):
        self.patient_model = patient_model

    def _set_user(self, request):
        self.user = request.user

    def _create_registry_specific_patient_form_class(self, user, form_class, registry_model):
        additional_fields = OrderedDict()
        field_pairs = self._get_registry_specific_fields(user, registry_model)
        if not field_pairs:
            return form_class

        for cde, field_object in field_pairs:
            additional_fields[cde.code] = field_object

        new_form_class = type(form_class.__name__, (form_class,), additional_fields)
        return new_form_class

    def _get_registry_specific_section_fields(self, user, registry_model):
        field_pairs = self._get_registry_specific_fields(user, registry_model)
        fieldset_title = registry_model.specific_fields_section_title
        field_list = [pair[0].code for pair in field_pairs]
        return fieldset_title, field_list

    def get_form(self, form_class=None):
        """
        PatientFormMixin.get_form Returns an instance of the form to be used in this view.
        """
        if form_class is None:
            form_class = self.get_form_class()

        form_instance = super(PatientFormMixin, self).get_form(form_class)
        self.patient_form = form_instance
        return form_instance

    def get_context_data(self, **kwargs):
        """
        :param kwargs: The kwargs supplied to render to response
        :return:
        """
        patient_id = self._get_patient_id()
        patient_address_formset = kwargs.get("patient_address_formset", None)
        patient_doctor_formset = kwargs.get("patient_doctor_formset", None)
        patient_relative_formset = kwargs.get("patient_relative_formset", None)

        patient, forms_sections = self._get_patient_and_forms_sections(patient_id,
                                                                       self.registry_model.code,
                                                                       self.request,
                                                                       self.patient_form,
                                                                       patient_address_form=patient_address_formset,
                                                                       patient_doctor_form=patient_doctor_formset,
                                                                       patient_relative_form=patient_relative_formset)

        error_messages = get_error_messages([pair[0] for pair in forms_sections])

        num_errors = len(error_messages)
        kwargs["forms"] = forms_sections
        kwargs["patient"] = patient
        # Avoid spurious errors message when we first hit the Add screen:
        kwargs["errors"] = True if num_errors > 0 and any(
            [not form[0].is_valid() for form in forms_sections]) else False

        if "all_errors" in kwargs:
            kwargs["errors"] = True
            kwargs["error_messages"] = kwargs["all_errors"]
        else:
            kwargs["error_messages"] = error_messages
        kwargs["registry_code"] = self.registry_model.code
        kwargs["location"] = _("Demographics")
        section_blacklist = self._check_for_blacklisted_sections(self.registry_model)
        kwargs["section_blacklist"] = section_blacklist

        section_hiddenlist = self._check_for_hidden_section(self.request.user,
                                                            self.registry_model,
                                                            forms_sections)
        kwargs["section_hiddenlist"] = section_hiddenlist
        if self.request.user.is_parent:
            kwargs['parent'] = ParentGuardian.objects.get(user=self.request.user)
        return kwargs

    def _extract_error_messages(self, form_pairs):
        # forms is a list of (form, field_info_list) pairs
        error_messages = []
        for form, info in form_pairs:
            if not form.is_valid():
                for error in form.errors:
                    error_messages.append(form.errors[error])
        return list(map(strip_tags, error_messages))

    def _get_patient_id(self):
        if self.object:
            return self.object.pk
        else:
            return None

    def _get_patient_and_forms_sections(self,
                                        patient_id,
                                        registry_code,
                                        request,
                                        patient_form=None,
                                        patient_address_form=None,
                                        patient_doctor_form=None,
                                        patient_relative_form=None):

        user = request.user
        if patient_id is None:
            patient = None
        else:
            patient = Patient.objects.get(id=patient_id)

        registry = Registry.objects.get(code=registry_code)

        if not patient_form:
            if not registry.patient_fields:
                patient_form = PatientForm(instance=patient, user=user, registry_model=registry)
            else:
                munged_patient_form_class = self._create_registry_specific_patient_form_class(
                    user,
                    PatientForm,
                    registry)
                patient_form = munged_patient_form_class(
                    instance=patient, user=user, registry_model=registry)

        patient_form.user = user

        if not patient_address_form:
            patient_address_formset = inlineformset_factory(Patient,
                                                            PatientAddress,
                                                            form=PatientAddressForm,
                                                            extra=0,
                                                            can_delete=True,
                                                            fields="__all__")

            patient_address_form = patient_address_formset(
                instance=patient, prefix="patient_address")

        personal_header = _('Patients Personal Details')
        # shouldn't be hardcoding behaviour here plus the html formatting
        # originally here was not being passed as text
        if registry_code == "fkrp":
            personal_header += " " + \
                _("Here you can find an overview of all your personal and contact details you have given us. You can update your contact details by changing the information below.")

        personal_details_fields = (personal_header, [
            "family_name",
            "given_names",
            "maiden_name",
            "umrn",
            "date_of_birth",
            "date_of_death",
            "place_of_birth",
            "date_of_migration",
            "country_of_birth",
            "ethnic_origin",
            "sex",
            "home_phone",
            "mobile_phone",
            "work_phone",
            "email",
            "living_status",
        ])

        next_of_kin = (_("Next of Kin"), [
            "next_of_kin_family_name",
            "next_of_kin_given_names",
            "next_of_kin_relationship",
            "next_of_kin_address",
            "next_of_kin_suburb",
            "next_of_kin_country",
            "next_of_kin_state",
            "next_of_kin_postcode",
            "next_of_kin_home_phone",
            "next_of_kin_mobile_phone",
            "next_of_kin_work_phone",
            "next_of_kin_email",
            "next_of_kin_parent_place_of_birth"
        ])

        rdrf_registry = (_("Centres"), [
            "rdrf_registry",
            "working_groups",
            "clinician"
        ])

        patient_address_section = (_("Patient Address"), None)

        form_sections = [
            (
                patient_form,
                (rdrf_registry,)
            ),
            (
                patient_form,
                (personal_details_fields,)
            ),
            (
                patient_address_form,
                (patient_address_section,)
            ),
            (
                patient_form,
                (next_of_kin,)
            ),
        ]

        if registry.has_feature("family_linkage"):
            form_sections = form_sections[:-1]

        if registry.get_metadata_item("patient_form_doctors"):
            if not patient_doctor_form:
                patient_doctor_formset = inlineformset_factory(Patient, Patient.doctors.through,
                                                               form=PatientDoctorForm,
                                                               extra=0,
                                                               can_delete=True,
                                                               fields="__all__")

                patient_doctor_form = patient_doctor_formset(
                    instance=patient, prefix="patient_doctor")

            patient_doctor_section = (_("Patient Doctor"), None)

            form_sections.append((
                patient_doctor_form,
                (patient_doctor_section,)
            ))

        # PatientRelativeForm for FH (only)
        if self.registry_model.has_feature('family_linkage'):
            if not patient_relative_form:
                patient_relative_formset = inlineformset_factory(Patient,
                                                                 PatientRelative,
                                                                 fk_name='patient',
                                                                 form=PatientRelativeForm,
                                                                 extra=0,
                                                                 can_delete=True,
                                                                 fields="__all__")

                patient_relative_form = patient_relative_formset(
                    instance=patient, prefix="patient_relative")

            patient_relative_section = (_("Patient Relative"), None)

            form_sections.append((patient_relative_form, (patient_relative_section,)))

        if registry.patient_fields:
            registry_specific_section_fields = self._get_registry_specific_section_fields(
                user, registry)
            form_sections.append(
                (patient_form, (registry_specific_section_fields,))
            )

        return patient, form_sections

    def get_form_kwargs(self):
        kwargs = super(PatientFormMixin, self).get_form_kwargs()
        # NB This means we must be mixed in with a View ( which we are)
        kwargs["user"] = self.request.user
        kwargs["registry_model"] = self.registry_model
        return kwargs

    def form_valid(self, form):
        # called _after_ all form(s) validated
        # save patient
        self.object = form.save()
        # if this patient was created from a patient relative, sync with it
        self.object.sync_patient_relative()

        # save registry specific fields
        registry_specific_fields_handler = RegistrySpecificFieldsHandler(
            self.registry_model, self.object)

        registry_specific_fields_handler.save_registry_specific_data_in_mongo(self.request)

        # save addresses
        if self.address_formset:
            self.address_formset.instance = self.object
            self.address_formset.save()

        # save doctors
        if self.registry_model.get_metadata_item("patient_form_doctors"):
            if self.doctor_formset:
                self.doctor_formset.instance = self.object
                self.doctor_formset.save()

        # patient relatives
        if self.patient_relative_formset:
            self.patient_relative_formset.instance = self.object
            patient_relative_models = self.patient_relative_formset.save()
            for patient_relative_model in patient_relative_models:
                patient_relative_model.patient = self.object
                patient_relative_model.save()
                patient_relative_model.sync_relative_patient()
                tag = patient_relative_model.given_names + patient_relative_model.family_name
                # The patient relative form has a checkbox to "create a patient from the
                # relative"
                for form in self.patient_relative_formset:
                    if form.tag == tag:  # must be a better way to do this ...
                        if form.create_patient_flag:
                            patient_relative_model.create_patient_from_myself(
                                self.registry_model,
                                self.object.working_groups.all())

        return HttpResponseRedirect(self.get_success_url())

    def _run_consent_closures(self, patient_model, registry_ids):
        if hasattr(patient_model, "add_registry_closures"):
            for closure in patient_model.add_registry_closures:
                closure(patient_model, registry_ids)
            delattr(patient_model, 'add_registry_closures')

    def form_invalid(self, patient_form,
                     patient_address_formset,
                     patient_doctor_formset,
                     patient_relative_formset,
                     errors):
        has_errors = len(errors) > 0
        return self.render_to_response(
            self.get_context_data(
                form=patient_form,
                all_errors=errors,
                errors=has_errors,
                patient_address_formset=patient_address_formset,
                patient_doctor_formset=patient_doctor_formset,
                patient_relative_formset=patient_relative_formset))

    def _get_address_formset(self, request):
        patient_address_form_set = inlineformset_factory(
            Patient, PatientAddress, form=PatientAddressForm, fields="__all__")
        return patient_address_form_set(request.POST, prefix="patient_address")

    def _get_doctor_formset(self, request):
        patient_doctor_form_set = inlineformset_factory(
            Patient, PatientDoctor, form=PatientDoctorForm, fields="__all__")
        return patient_doctor_form_set(request.POST, prefix="patient_doctor")

    def _get_patient_relatives_formset(self, request):
        patient_relatives_formset = inlineformset_factory(Patient,
                                                          PatientRelative,
                                                          fk_name='patient',
                                                          form=PatientRelativeForm,
                                                          extra=0,
                                                          can_delete=True,
                                                          fields="__all__")

        return patient_relatives_formset(request.POST, prefix="patient_relative")

    def _has_doctors_form(self):
        return self.registry_model.get_metadata_item("patient_form_doctors")

    def _has_patient_relatives_form(self):
        return self.registry_model.has_feature("family_linkage")


class AddPatientView(PatientFormMixin, CreateView):
    model = Patient
    form_class = PatientForm
    template_name = 'rdrf_cdes/generic_patient.html'

    @method_decorator(anonymous_not_allowed)
    @method_decorator(login_required)
    def get(self, request, registry_code):

        registry = Registry.objects.get(code=registry_code)
        if registry.has_feature("no_add_patient_button"):
            raise Http404()

        logger.info("PATIENTADD %s %s" % (request.user,
                                          registry_code))
        if not request.user.is_authenticated:
            patient_add_url = reverse('patient_add', args=[registry_code])
            login_url = reverse('two_factor:login')
            return redirect("%s?next=%s" % (login_url, patient_add_url))

        self._set_registry_model(registry_code)
        self._set_user(request)
        return super(AddPatientView, self).get(request, registry_code)

    @method_decorator(anonymous_not_allowed)
    @method_decorator(login_required)
    def post(self, request, registry_code):
        self.request = request
        self._set_user(request)
        self._set_registry_model(registry_code)
        forms = []
        patient_form_class = self.get_form_class()
        patient_form = self.get_form(patient_form_class)

        country_code = request.POST.get('country_of_birth')
        patient_form.fields['country_of_birth'].choices = [(country_code, country_code)]

        kin_country_code = request.POST.get('next_of_kin_country')
        kin_state_code = request.POST.get('next_of_kin_state')
        patient_form.fields['next_of_kin_country'].choices = [(kin_country_code, kin_country_code)]
        patient_form.fields['next_of_kin_state'].choices = [(kin_state_code, kin_state_code)]

        forms.append(patient_form)

        self.address_formset = self._get_address_formset(request)
        index = 0
        for f in self.address_formset.forms:
            country_field_name = 'patient_address-' + str(index) + '-country'
            patient_country_code = request.POST.get(country_field_name)
            state_field_name = 'patient_address-' + str(index) + '-state'
            patient_state_code = request.POST.get(state_field_name)
            index += 1
            f.fields['country'].choices = [(patient_country_code, patient_country_code)]
            f.fields['state'].choices = [(patient_state_code, patient_state_code)]

        forms.append(self.address_formset)

        if self._has_doctors_form():
            self.doctor_formset = self._get_doctor_formset(request)
            forms.append(self.doctor_formset)

        if self._has_patient_relatives_form():
            self.patient_relative_formset = self._get_patient_relatives_formset(request)
            forms.append(self.patient_relative_formset)

        if all([form.is_valid() for form in forms]):
            return self.form_valid(patient_form)
        else:
            errors = get_error_messages(forms)

            return self.form_invalid(patient_form=patient_form,
                                     patient_address_formset=self.address_formset,
                                     patient_doctor_formset=self.doctor_formset,
                                     patient_relative_formset=self.patient_relative_formset,
                                     errors=errors)

    def _check_for_blacklisted_sections(self, registry_model):
        if "section_blacklist" in registry_model.metadata:
            section_blacklist = registry_model.metadata["section_blacklist"]
            section_blacklist = [_(x) for x in section_blacklist]
        else:
            section_blacklist = []

        return section_blacklist

    def _check_for_hidden_section(self, user, registry, form_sections):
        section_hiddenlist = []
        for form, sections in form_sections:
            for name, section in sections:
                if section is not None:
                    if self._section_hidden(user, registry, section):
                        section_hiddenlist.append(name)
        return section_hiddenlist

    def _section_hidden(self, user, registry, fieldlist):
        from rdrf.models.definition.models import DemographicFields
        user_groups = [g.name for g in user.groups.all()]
        hidden_fields = DemographicFields.objects.filter(field__in=fieldlist,
                                                         registry=registry,
                                                         group__name__in=user_groups,
                                                         hidden=True)

        return (len(fieldlist) == hidden_fields.count())


class PatientEditView(View):

    def _check_for_blacklisted_sections(self, registry_model):
        if "section_blacklist" in registry_model.metadata:
            section_blacklist = registry_model.metadata["section_blacklist"]
            section_blacklist = [_(x) for x in section_blacklist]
        else:
            section_blacklist = []

        return section_blacklist

    def load_custom_actions(self, registry_model, user, patient_model):
        if user and patient_model and registry_model:
            return [CustomActionWrapper(registry_model,
                                        user,
                                        custom_action,
                                        patient_model) for custom_action in
                    user.get_custom_actions_by_scope(registry_model)]
        else:
            return []

    @method_decorator(anonymous_not_allowed)
    @method_decorator(login_required)
    def get(self, request, registry_code, patient_id):
        logger.info("DEMOGRAPHICSGET %s %s %s" % (request.user,
                                                  registry_code,
                                                  patient_id))
        if not request.user.is_authenticated:
            patient_edit_url = reverse('patient_edit', args=[registry_code, patient_id, ])
            login_url = reverse('two_factor:login')
            return redirect("%s?next=%s" % (login_url, patient_edit_url))

        registry_model = Registry.objects.get(code=registry_code)

        section_blacklist = self._check_for_blacklisted_sections(registry_model)

        patient, form_sections = self._get_patient_and_forms_sections(patient_id, registry_code, request)

        security_check_user_patient(request.user, patient)

        if registry_model.has_feature("consent_checks"):
            from rdrf.helpers.utils import consent_check
            if not consent_check(registry_model,
                                 request.user,
                                 patient,
                                 "see_patient"):
                raise PermissionDenied

        context_launcher = RDRFContextLauncherComponent(
            request.user, registry_model, patient, rdrf_nonce=request.csp_nonce)
        patient_info = RDRFPatientInfoComponent(registry_model, patient)

        family_linkage_panel = FamilyLinkagePanel(request.user,
                                                  registry_model,
                                                  patient)

        context = {
            "location": "Demographics",
            "context_launcher": context_launcher.html,
            "patient_info": patient_info.html,
            "forms": form_sections,
            "family_linkage_panel": family_linkage_panel.html,
            "patient": patient,
            "proms_link": self._get_proms_link(registry_model, patient),
            "patient_id": patient.id,
            "registry_code": registry_code,
            "form_links": [],
            "show_archive_button": request.user.can_archive,
            "archive_patient_url": patient.get_archive_url(registry_model) if request.user.can_archive else "",
            "consent": consent_status_for_patient(
                registry_code,
                patient),
            "section_blacklist": section_blacklist}
        if request.GET.get('just_created', False):
            context["message"] = _("Patient added successfully")

        context["not_linked"] = not patient.is_linked

        wizard = NavigationWizard(request.user,
                                  registry_model,
                                  patient,
                                  NavigationFormType.DEMOGRAPHICS,
                                  None,
                                  None)

        context["next_form_link"] = wizard.next_link
        context["previous_form_link"] = wizard.previous_link

        if request.user.is_parent:
            context['parent'] = ParentGuardian.objects.get(user=request.user)

        hidden_sectionlist = self._check_for_hidden_section(request.user,
                                                            registry_model,
                                                            form_sections)
        context["hidden_sectionlist"] = hidden_sectionlist

        context['custom_actions'] = self.load_custom_actions(registry_model, request.user, patient)

        return render(request, 'rdrf_cdes/patient_edit.html', context)

    def _get_proms_link(self, registry_model, patient_model):
        if not registry_model.has_feature("proms_clinical"):
            return None
        return "todo"

    @method_decorator(anonymous_not_allowed)
    @method_decorator(login_required)
    def post(self, request, registry_code, patient_id):
        logger.info("DEMOGRAPHICSPOST %s %s %s" % (request.user,
                                                   registry_code,
                                                   patient_id))

        user = request.user
        patient = Patient.objects.get(id=patient_id)
        patient_type = patient.patient_type
        security_check_user_patient(user, patient)

        patient_relatives_forms = None
        actions = []

        if patient.user:
            patient_user = patient.user
        else:
            patient_user = None

        registry_model = Registry.objects.get(code=registry_code)

        context_launcher = RDRFContextLauncherComponent(
            request.user, registry_model, patient, rdrf_nonce=request.csp_nonce)
        patient_info = RDRFPatientInfoComponent(registry_model, patient)

        if registry_model.patient_fields:
            patient_form_class = self._create_registry_specific_patient_form_class(
                user, PatientForm, registry_model, patient)
        else:
            patient_form_class = PatientForm

        patient_form = patient_form_class(
            request.POST,
            request.FILES,
            instance=patient,
            user=request.user,
            registry_model=registry_model)

        country_code = request.POST.get('country_of_birth')
        patient_form.fields['country_of_birth'].choices = [(country_code, country_code)]

        kin_country_code = request.POST.get('next_of_kin_country')
        kin_state_code = request.POST.get('next_of_kin_state')
        patient_form.fields['next_of_kin_country'].choices = [(kin_country_code, kin_country_code)]
        patient_form.fields['next_of_kin_state'].choices = [(kin_state_code, kin_state_code)]

        patient_address_form_set = inlineformset_factory(
            Patient, PatientAddress, form=PatientAddressForm, fields="__all__")
        address_to_save = patient_address_form_set(
            request.POST, instance=patient, prefix="patient_address")

        index = 0
        for f in address_to_save.forms:
            country_field_name = 'patient_address-' + str(index) + '-country'
            patient_country_code = request.POST.get(country_field_name)
            state_field_name = 'patient_address-' + str(index) + '-state'
            patient_state_code = request.POST.get(state_field_name)
            index += 1
            f.fields['country'].choices = [(patient_country_code, patient_country_code)]
            f.fields['state'].choices = [(patient_state_code, patient_state_code)]

        patient_relatives_forms = None

        if patient.is_index and registry_model.get_metadata_item("family_linkage"):
            patient_relatives_formset = inlineformset_factory(Patient,
                                                              PatientRelative,
                                                              fk_name='patient',
                                                              form=PatientRelativeForm,
                                                              extra=0,
                                                              can_delete=True,
                                                              fields="__all__")

            patient_relatives_forms = patient_relatives_formset(
                request.POST, instance=patient, prefix="patient_relative")

            forms = [patient_form, address_to_save, patient_relatives_forms]
        else:
            forms = [patient_form, address_to_save]

        valid_forms = []
        error_messages = []

        for form in forms:
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

        if registry_model.get_metadata_item("patient_form_doctors"):
            patient_doctor_form_set = inlineformset_factory(
                Patient, PatientDoctor, form=PatientDoctorForm, fields="__all__")
            doctors_to_save = patient_doctor_form_set(
                request.POST, instance=patient, prefix="patient_doctor")
            valid_forms.append(doctors_to_save.is_valid())

        if all(valid_forms):
            if registry_model.get_metadata_item("patient_form_doctors"):
                doctors_to_save.save()
            address_to_save.save()
            patient_instance = patient_form.save()
            patient_instance.patient_type = patient_type
            patient_instance.save()

            patient_instance.sync_patient_relative()

            if patient_user and not patient_instance.user:
                patient_instance.user = patient_user
                patient_instance.save()

            registry_specific_fields_handler = RegistrySpecificFieldsHandler(
                registry_model, patient_instance)
            registry_specific_fields_handler.save_registry_specific_data_in_mongo(request)

            patient, form_sections = self._get_patient_and_forms_sections(
                patient_id, registry_code, request)

            if patient_relatives_forms:
                self.create_patient_relatives(patient_relatives_forms, patient, registry_model)

            context = {
                "forms": form_sections,
                "patient": patient,
                "context_launcher": context_launcher.html,
                "message": _("Patient's details saved successfully"),
                "error_messages": [],
            }
        else:
            error_messages = get_error_messages(forms)
            if not registry_model.get_metadata_item("patient_form_doctors"):
                doctors_to_save = None
            patient, form_sections = self._get_patient_and_forms_sections(patient_id,
                                                                          registry_code,
                                                                          request,
                                                                          patient_form,
                                                                          address_to_save,
                                                                          doctors_to_save,
                                                                          patient_relatives_forms=patient_relatives_forms)

            context = {
                "forms": form_sections,
                "patient": patient,
                "actions": actions,
                "context_launcher": context_launcher.html,
                "errors": True,
                "error_messages": error_messages,
            }

        wizard = NavigationWizard(request.user,
                                  registry_model,
                                  patient,
                                  NavigationFormType.DEMOGRAPHICS,
                                  None,
                                  None)

        family_linkage_panel = FamilyLinkagePanel(request.user,
                                                  registry_model,
                                                  patient)

        context["next_form_link"] = wizard.next_link
        context["previous_form_link"] = wizard.previous_link
        context["patient_info"] = patient_info.html

        context["registry_code"] = registry_code
        context["patient_id"] = patient.id
        context["location"] = _("Demographics")
        context["form_links"] = []
        context["not_linked"] = not patient.is_linked
        context["family_linkage_panel"] = family_linkage_panel.html
        context["show_archive_button"] = request.user.can_archive
        context["archive_patient_url"] = patient.get_archive_url(
            registry_model) if request.user.can_archive else ""
        context["consent"] = consent_status_for_patient(registry_code, patient)

        section_blacklist = self._check_for_blacklisted_sections(registry_model)
        context["section_blacklist"] = section_blacklist

        hidden_sectionlist = self._check_for_hidden_section(request.user,
                                                            registry_model,
                                                            form_sections)
        context["hidden_sectionlist"] = hidden_sectionlist
        context['custom_actions'] = self.load_custom_actions(registry_model, request.user, patient)

        if request.user.is_parent:
            context['parent'] = ParentGuardian.objects.get(user=request.user)

        return render(request, 'rdrf_cdes/patient_edit.html', context)

    def _is_linked(self, registry_model, patient_model):
        # is this patient linked to others?
        if not registry_model.has_feature("family_linkage"):
            return False

        if not patient_model.is_index:
            return False

        for patient_relative in patient_model.relatives.all():
            if patient_relative.relative_patient:
                return True

        return False

    def create_patient_relatives(self, patient_relative_formset, patient_model, registry_model):
        if patient_relative_formset:
            patient_relative_formset.instance = patient_model
            patient_relative_models = patient_relative_formset.save()
            for patient_relative_model in patient_relative_models:
                patient_relative_model.patient = patient_model
                patient_relative_model.save()
                # explicitly synchronise with the patient that has already been created from
                # this patient relative ( if any )
                # to avoid infinite loops we are doing this explicitly in the views ( not
                # overriding save)
                patient_relative_model.sync_relative_patient()

                tag = patient_relative_model.given_names + patient_relative_model.family_name
                # The patient relative form has a checkbox to "create a patient from the
                # relative"
                for form in patient_relative_formset:
                    if form.tag == tag:  # must be a better way to do this ...
                        if form.create_patient_flag:
                            patient_relative_model.create_patient_from_myself(
                                registry_model,
                                patient_model.working_groups.all())

    def _get_patient_and_forms_sections(self,
                                        patient_id,
                                        registry_code,
                                        request,
                                        patient_form=None,
                                        patient_address_form=None,
                                        patient_doctor_form=None,
                                        patient_relatives_forms=None):

        user = request.user
        hide_registry_specific_fields_section = False

        try:
            if patient_id is None:
                patient = None
            else:
                patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            raise Http404()

        registry = Registry.objects.get(code=registry_code)

        if not patient_form:
            if not registry.patient_fields:
                patient_form = PatientForm(instance=patient, user=user, registry_model=registry)
            else:
                munged_patient_form_class = self._create_registry_specific_patient_form_class(
                    user,
                    PatientForm,
                    registry,
                    patient)
                if munged_patient_form_class.HIDDEN:
                    hide_registry_specific_fields_section = True
                patient_form = munged_patient_form_class(
                    instance=patient, user=user, registry_model=registry)

        if not patient_address_form:
            patient_address_formset = inlineformset_factory(Patient,
                                                            PatientAddress,
                                                            form=PatientAddressForm,
                                                            extra=0,
                                                            can_delete=True,
                                                            fields="__all__")

            patient_address_form = patient_address_formset(
                instance=patient, prefix="patient_address")

        personal_details_fields = (_('Patients Personal Details'), [
            "family_name",
            "given_names",
            "maiden_name",
            "umrn",
            "date_of_birth",
            "date_of_death",
            "place_of_birth",
            "date_of_migration",
            "country_of_birth",
            "ethnic_origin",
            "sex",
            "home_phone",
            "mobile_phone",
            "work_phone",
            "email",
            "living_status",
        ])

        next_of_kin = (_("Next of Kin"), [
            "next_of_kin_family_name",
            "next_of_kin_given_names",
            "next_of_kin_relationship",
            "next_of_kin_address",
            "next_of_kin_suburb",
            "next_of_kin_country",
            "next_of_kin_state",
            "next_of_kin_postcode",
            "next_of_kin_home_phone",
            "next_of_kin_mobile_phone",
            "next_of_kin_work_phone",
            "next_of_kin_email",
            "next_of_kin_parent_place_of_birth"
        ])

        rdrf_registry = (_("Centres"), [
            "rdrf_registry",
            "working_groups",
            "clinician"
        ])

        patient_address_section = (_("Patient Address"), None)

        form_sections = [
            (
                patient_form,
                (rdrf_registry,)
            ),
            (
                patient_form,
                (personal_details_fields,)
            ),
            (
                patient_address_form,
                (patient_address_section,)
            ),
            (
                patient_form,
                (next_of_kin,)
            ),
        ]

        if registry.has_feature("family_linkage"):
            form_sections = form_sections[:-1]

        if registry.get_metadata_item("patient_form_doctors"):
            if not patient_doctor_form:
                patient_doctor_formset = inlineformset_factory(Patient, Patient.doctors.through,
                                                               form=PatientDoctorForm,
                                                               extra=0,
                                                               can_delete=True,
                                                               fields="__all__")

                patient_doctor_form = patient_doctor_formset(
                    instance=patient, prefix="patient_doctor")

            patient_doctor_section = (_("Patient Doctor"), None)

            form_sections.append((
                patient_doctor_form,
                (patient_doctor_section,)
            ))

        # PatientRelativeForm
        if patient.is_index:
            patient_relative_formset = inlineformset_factory(Patient,
                                                             PatientRelative,
                                                             fk_name='patient',
                                                             form=PatientRelativeForm,
                                                             extra=0,
                                                             can_delete=True,
                                                             fields="__all__")

            if patient_relatives_forms is None:

                patient_relative_form = patient_relative_formset(
                    instance=patient, prefix="patient_relative")

            else:
                patient_relative_form = patient_relatives_forms

            patient_relative_section = (_("Patient Relative"), None)

            form_sections.append((patient_relative_form, (patient_relative_section,)))

        if registry.patient_fields:
            if not hide_registry_specific_fields_section:
                registry_specific_section_fields = self._get_registry_specific_section_fields(
                    user, registry)
                form_sections.append(
                    (patient_form, (registry_specific_section_fields,))
                )

        return patient, form_sections

    def _get_registry_specific_fields(self, user, registry_model):
        """
        return: list of cde_model, field_object pairs
        """
        if user.is_superuser:
            return registry_model.patient_fields
        if registry_model not in user.registry.all():
            return []
        else:
            return registry_model.patient_fields

    def _create_registry_specific_patient_form_class(
            self, user, form_class, registry_model, patient=None):
        additional_fields = OrderedDict()
        field_pairs = self._get_registry_specific_fields(user, registry_model)

        for cde, field_object in field_pairs:
            try:
                cde_policy = CdePolicy.objects.get(registry=registry_model, cde=cde)
            except CdePolicy.DoesNotExist:
                cde_policy = None

            if cde_policy is None:
                additional_fields[cde.code] = field_object
            else:

                if user.is_superuser or cde_policy.is_allowed(user.groups.all(), patient):
                    if patient.is_index:
                        additional_fields[cde.code] = field_object

        if len(list(additional_fields.keys())) == 0:
            additional_fields["HIDDEN"] = True
        else:
            additional_fields["HIDDEN"] = False

        new_form_class = type(form_class.__name__, (form_class,), additional_fields)
        return new_form_class

    def _get_registry_specific_section_fields(self, user, registry_model):
        field_pairs = self._get_registry_specific_fields(user, registry_model)
        fieldset_title = registry_model.specific_fields_section_title
        field_list = [pair[0].code for pair in field_pairs]
        return fieldset_title, field_list

    def _check_for_hidden_section(self, user, registry, form_sections):
        section_hiddenlist = []
        for form, sections in form_sections:
            for name, section in sections:
                if section is not None:
                    if self._section_hidden(user, registry, section):
                        section_hiddenlist.append(name)
        return section_hiddenlist

    def _section_hidden(self, user, registry, fieldlist):
        from rdrf.models.definition.models import DemographicFields
        user_groups = [g.name for g in user.groups.all()]
        hidden_fields = DemographicFields.objects.filter(field__in=fieldlist,
                                                         registry=registry,
                                                         group__name__in=user_groups,
                                                         hidden=True)

        return (len(fieldlist) == hidden_fields.count())


class QueryPatientView(View):
    @method_decorator(anonymous_not_allowed)
    @method_decorator(login_required)
    def get(self, request, registry_code):
        context = {'registry_code': registry_code}
        return render(request, "rdrf_cdes/patient_query.html", context)


class SimpleReadonlyPatientView(View):
    @method_decorator(anonymous_not_allowed)
    @method_decorator(login_required)
    def get(self, request, registry_code, patient_id):
        registry = self.get_registry(registry_code)
        user = request.user
        patient = self.get_patient(patient_id)
        template_name = self.get_template()
        actions = self.get_actions(registry, user)
        context = self.get_context(registry, user, patient)
        if not context:
            raise Http404
        context["actions"] = actions
        context["show_archive_button"] = request.user.can_archive
        context["context_launcher"] = self.get_context_launcher(registry,
                                                                patient,
                                                                request)

        return render(request, template_name, context)

    def get_patient(self, patient_id):
        try:
            return Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            raise Http404

    def get_context_launcher(self, registry, patient, request):
        context_launcher = RDRFContextLauncherComponent(request.user,
                                                        registry,
                                                        patient,
                                                        rdrf_nonce=request.csp_nonce)
        return context_launcher.html

    def get_registry(self, registry_code):
        try:
            return Registry.objects.get(code=registry_code)
        except Registry.DoesNotExist:
            raise Http404

    def get_context(self, registry, user, patient):
        pass

    def get_template(self):
        raise NotImplementedError()

    def get_actions(self, registry, user):
        return []


class ExternalDemographicsView(SimpleReadonlyPatientView):
    def get_context(self, registry, user, patient):
        context = {}
        # demographics_fields = []
        patient_fields = patient._meta.fields

        def get_label(field):
            return field.name

        def get_value(patient, field):
            return getattr(patient, field.name)

        context["field_pairs"] = [(get_label(field), get_value(patient, field)) for field in patient_fields]
        context["location"] = "Demographics"
        context["patient"] = patient

        return context

    def get_template(self):
        return "rdrf_cdes/external_demographics.html"
