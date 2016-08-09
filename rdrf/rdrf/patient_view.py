from collections import OrderedDict
from datetime import date

from django.shortcuts import render_to_response, RequestContext, redirect
from django.views.generic.base import View
from django.views.generic import CreateView
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.contrib.auth import logout

from rdrf.models import RegistryForm
from rdrf.models import Registry
from rdrf.models import CdePolicy
from rdrf.utils import FormLink
from rdrf.utils import get_form_links
from rdrf.utils import consent_status_for_patient
from rdrf.models import ConsentSection
from rdrf.models import ConsentQuestion
from form_progress import FormProgress

from django.forms.models import inlineformset_factory
from django.utils.html import strip_tags

from django.contrib.auth.models import Group

from registry.patients.models import Patient, PatientAddress, PatientDoctor, PatientRelative, PatientConsent, ParentGuardian, ConsentValue
from registry.patients.admin_forms import PatientForm, PatientAddressForm, PatientDoctorForm, PatientRelativeForm, PatientConsentFileForm
from django.utils.translation import ugettext as _

from rdrf.registry_specific_fields import RegistrySpecificFieldsHandler
from rdrf.utils import get_error_messages
from rdrf.wizard import NavigationWizard, NavigationFormType

from rdrf.contexts_api import RDRFContextManager, RDRFContextError
from rdrf.context_menu import PatientContextMenu
from rdrf.components import RDRFContextLauncherComponent

import logging

logger = logging.getLogger(__name__)


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
        logger.debug("set registry model to %s" % self.registry_model)

    def get_success_url(self):
        """
        After a successful add where to go?
        Returns the supplied success URL. (We override to redirect to edit screen for the newly added patient)
        """
        registry_code = self.registry_model.code
        patient_id = self.object.pk
        patient_edit_url = reverse('patient_edit', args=[registry_code, patient_id])
        return patient_edit_url

    def _get_initial_context(self, registry_code, patient_model):
        from rdrf.contexts_api import RDRFContextManager, RDRFContextError
        from rdrf.models import Registry
        registry_model = Registry.objects.get(code=registry_code)
        rdrf_context_manager = RDRFContextManager(registry_model)
        return rdrf_context_manager.get_or_create_default_context(patient_model, new_patient=True)

    def set_patient_model(self, patient_model):
        self.patient_model = patient_model

    def _set_user(self, request):
        self.user = request.user
        logger.debug("set user to %s" % self.user)

    def _create_registry_specific_patient_form_class(self, user, form_class, registry_model):
        logger.debug("creating registry specific patient form ...")
        additional_fields = OrderedDict()
        field_pairs = self._get_registry_specific_fields(user, registry_model)
        if not field_pairs:
            logger.debug("no registry specific fields - returning original form class")
            return form_class

        for cde, field_object in field_pairs:
            additional_fields[cde.code] = field_object
            logger.debug("adding new field %s" % cde.name)

        new_form_class = type(form_class.__name__, (form_class,), additional_fields)
        logger.debug("returning new form class")
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
        if self.request.method == "GET":
            logger.debug("get_context_data called by GET")
        else:
            logger.debug("get_context_data called by POST")

        logger.debug("in get_context_data ..")
        logger.debug("supplied kwargs = %s" % kwargs)
        patient_id = self._get_patient_id()

        patient_address_formset = kwargs.get("patient_address_formset", None)
        patient_doctor_formset = kwargs.get("patient_doctor_formset", None)
        patient_relative_formset = kwargs.get("patient_relative_formset", None)
        #patient_consent_file_formset = kwargs.get("patient_consent_file_formset", None)

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
        kwargs["context_instance"] = RequestContext(self.request)
        logger.debug("updated kwargs = %s" % kwargs)
        kwargs["location"] = _("Demographics")
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
        return map(strip_tags, error_messages)

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
        if registry_code == "fkrp":
            personal_header += "<br><br><i>" + \
                _("Here you can find an overview of all your personal and contact details you have given us. You can update your contact details by changing the information below.") + "</i>"

        personal_details_fields = (personal_header, [
            "family_name",
            "given_names",
            "maiden_name",
            "umrn",
            "date_of_birth",
            "place_of_birth",
            "country_of_birth",
            "ethnic_origin",
            "sex",
            "home_phone",
            "mobile_phone",
            "work_phone",
            "email",
            "living_status",
        ])

        next_of_kin = ("Next of Kin", [
            "next_of_kin_family_name",
            "next_of_kin_given_names",
            "next_of_kin_relationship",
            "next_of_kin_address",
            "next_of_kin_country",
            "next_of_kin_suburb",
            "next_of_kin_state",
            "next_of_kin_postcode",
            "next_of_kin_home_phone",
            "next_of_kin_mobile_phone",
            "next_of_kin_work_phone",
            "next_of_kin_email",
            "next_of_kin_parent_place_of_birth"
        ])

        rdrf_registry = ("Registry", [
            "rdrf_registry",
            "working_groups",
            "clinician"
        ])

        patient_address_section = ("Patient Address", None)

        # patient_consent_file_formset = inlineformset_factory(
        #     Patient, PatientConsent, form=PatientConsentFileForm, extra=0, can_delete=True, fields="__all__")
        # patient_consent_file_form = patient_consent_file_formset(
        #     instance=patient, prefix="patient_consent_file")
        #
        # patient_section_consent = patient_form.get_all_consent_section_info(
        #     patient, registry_code)
        # patient_section_consent_file = (_("Upload Consent File"), None)

        form_sections = [
            # (
            #     patient_form,
            #     patient_section_consent
            # ),
            # (
            #     patient_consent_file_form,
            #     (patient_section_consent_file,)
            # ),
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
        logger.debug("get form kwargs = %s" % kwargs)
        return kwargs

    def form_valid(self, form):
        # called _after_ all form(s) validated
        # save patient
        self.object = form.save()
        # if this patient was created from a patient relative, sync with it
        self.object.sync_patient_relative()

        # save registry specific fields
        registry_specific_fields_handler = RegistrySpecificFieldsHandler(self.registry_model, self.object)

        registry_specific_fields_handler.save_registry_specific_data_in_mongo(self.request)

        # if self.patient_consent_file_formset:
        #     self.patient_consent_file_formset.instance = self.object
        #     self.patient_consent_file_formset.save()

        # save addresses
        if self.address_formset:
            self.address_formset.instance = self.object
            addresses = self.address_formset.save()
            logger.debug("saved addresses %s OK" % addresses)

        # save doctors
        if self.registry_model.get_metadata_item("patient_form_doctors"):
            if self.doctor_formset:
                self.doctor_formset.instance = self.object
                doctors = self.doctor_formset.save()
                logger.debug("saved doctors %s OK" % doctors)

        # patient relatives
        if self.patient_relative_formset:
            self.patient_relative_formset.instance = self.object
            patient_relative_models = self.patient_relative_formset.save()
            for patient_relative_model in patient_relative_models:
                patient_relative_model.patient = self.object
                patient_relative_model.save()
                patient_relative_model.sync_relative_patient()
                logger.debug("saved patient relative model %s OK - owning patient is %s" % (patient_relative_model,
                                                                                            patient_relative_model.patient))
                tag = patient_relative_model.given_names + patient_relative_model.family_name
                # The patient relative form has a checkbox to "create a patient from the
                # relative"
                for form in self.patient_relative_formset:
                    if form.tag == tag:  # must be a better way to do this ...
                        logger.debug("patient tag = %s" % form.tag)
                        if form.create_patient_flag:
                            logger.debug("creating patient from relative %s" %
                                         patient_relative_model)

                            patient_relative_model.create_patient_from_myself(
                                self.registry_model,
                                self.object.working_groups.all())
                        else:
                            logger.debug("create_patient_flag is False ...")
                    else:
                        logger.debug("form tag different")

        #patient_model = self.object
        # if hasattr(patient_model, 'add_registry_closures'):
        #     registry_ids = [reg.id for reg in patient_model.rdrf_registry.all()]
        #     self._run_consent_closures(patient_model, registry_ids)
        # else:
        #     logger.debug("self.object has no closures")

        return HttpResponseRedirect(self.get_success_url())

    def _run_consent_closures(self, patient_model, registry_ids):
        logger.debug("reg ids = %s" % registry_ids)
        if hasattr(patient_model, "add_registry_closures"):
            for closure in patient_model.add_registry_closures:
                closure(patient_model, registry_ids)
            delattr(patient_model, 'add_registry_closures')
        else:
            logger.debug("patient model does not have closure list")

    def form_invalid(self, patient_form,
                     patient_address_formset,
                     patient_doctor_formset,
                     patient_relative_formset,
                     errors):
        logger.debug("errors = %s" % errors)
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

    def get(self, request, registry_code):
        if not request.user.is_authenticated():
            patient_add_url = reverse('patient_add', args=[registry_code])
            login_url = reverse('login')
            return redirect("%s?next=%s" % (login_url, patient_add_url))

        self._set_registry_model(registry_code)
        self._set_user(request)
        return super(AddPatientView, self).get(request, registry_code)

    def post(self, request, registry_code):
        self.request = request
        logger.debug("starting POST of Add Patient")
        self._set_user(request)
        self._set_registry_model(registry_code)
        forms = []
        patient_form_class = self.get_form_class()
        patient_form = self.get_form(patient_form_class)
        forms.append(patient_form)

        self.address_formset = self._get_address_formset(request)
        forms.append(self.address_formset)

        # patient_consent_file_formset = inlineformset_factory(
        #     Patient, PatientConsent, form=PatientConsentFileForm, fields="__all__")
        # self.patient_consent_file_formset = patient_consent_file_formset(
        #     request.POST, request.FILES, prefix="patient_consent_file")
        # forms.append(self.patient_consent_file_formset)

        if self._has_doctors_form():
            self.doctor_formset = self._get_doctor_formset(request)
            forms.append(self.doctor_formset)

        if self._has_patient_relatives_form():
            self.patient_relative_formset = self._get_patient_relatives_formset(request)
            forms.append(self.patient_relative_formset)

        if all([form.is_valid() for form in forms]):
            logger.debug("all forms valid ... ")
            return self.form_valid(patient_form)
        else:
            logger.debug("some forms are invalid ...")
            errors = get_error_messages(forms)
            logger.debug(errors)

            return self.form_invalid(patient_form=patient_form,
                                     patient_address_formset=self.address_formset,
                                     patient_doctor_formset=self.doctor_formset,
                                     patient_relative_formset=self.patient_relative_formset,
                                     errors=errors)


class PatientEditView(View):

    def get(self, request, registry_code, patient_id):
        if not request.user.is_authenticated():
            patient_edit_url = reverse('patient_edit', args=[registry_code, patient_id, ])
            login_url = reverse('login')
            return redirect("%s?next=%s" % (login_url, patient_edit_url))

        patient, form_sections = self._get_patient_and_forms_sections(
            patient_id, registry_code, request)
        registry_model = Registry.objects.get(code=registry_code)

        context_launcher = RDRFContextLauncherComponent(request.user, registry_model, patient)

        context = {
            "location": "Demographics",
            "context_launcher": context_launcher.html,
            "forms": form_sections,
            "patient": patient,
            "patient_id": patient.id,
            "registry_code": registry_code,
            "form_links": [],
            "consent": consent_status_for_patient(registry_code, patient)
        }

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

        return render_to_response(
            'rdrf_cdes/patient_edit.html',
            context,
            context_instance=RequestContext(request))

    def post(self, request, registry_code, patient_id):
        user = request.user
        patient = Patient.objects.get(id=patient_id)
        patient_relatives_forms = None
        actions = []

        logger.debug("Edit patient pk before save %s" % patient.pk)

        if patient.user:
            logger.debug("patient user before save = %s" % patient.user)
            patient_user = patient.user
        else:
            patient_user = None
            logger.debug("patient user before save is None")

        registry_model = Registry.objects.get(code=registry_code)

        context_launcher = RDRFContextLauncherComponent(request.user, registry_model, patient)

        if registry_model.patient_fields:
            patient_form_class = self._create_registry_specific_patient_form_class(user,
                                                                                   PatientForm,
                                                                                   registry_model,
                                                                                   patient)

        else:
            patient_form_class = PatientForm

        patient_form = patient_form_class(
            request.POST, request.FILES, instance=patient, user=request.user, registry_model=registry_model)

        patient_address_form_set = inlineformset_factory(
            Patient, PatientAddress, form=PatientAddressForm, fields="__all__")
        address_to_save = patient_address_form_set(
            request.POST, instance=patient, prefix="patient_address")

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
            logger.debug("All forms are valid")
            if registry_model.get_metadata_item("patient_form_doctors"):
                doctors_to_save.save()
            address_to_save.save()
            patient_instance = patient_form.save()

            patient_instance.sync_patient_relative()

            logger.debug("patient pk after valid forms save = %s" % patient_instance.pk)

            # For some reason for FKRP , the patient.user was being clobbered
            logger.debug("patient.user after all valid forms saved = %s" % patient.user)
            if patient_user and not patient_instance.user:
                patient_instance.user = patient_user
                patient_instance.save()

            registry_specific_fields_handler = RegistrySpecificFieldsHandler(registry_model, patient_instance)
            registry_specific_fields_handler.save_registry_specific_data_in_mongo(request)

            patient, form_sections = self._get_patient_and_forms_sections(
                patient_id, registry_code, request)

            if patient_relatives_forms:
                self.create_patient_relatives(patient_relatives_forms, patient, registry_model)

            context = {
                "forms": form_sections,
                "patient": patient,
                "context_launcher": context_launcher.html,
                "message": "Patient's details saved successfully",
                "error_messages": [],
            }
        else:
            logger.debug("Not all forms are valid")
            error_messages = get_error_messages(forms)
            logger.debug("error messages = %s" % error_messages)
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

        context["next_form_link"] = wizard.next_link
        context["previous_form_link"] = wizard.previous_link

        context["registry_code"] = registry_code
        context["patient_id"] = patient.id
        context["location"] = _("Demographics")
        context["form_links"] = []
        context["consent"] = consent_status_for_patient(registry_code, patient)

        if request.user.is_parent:
            context['parent'] = ParentGuardian.objects.get(user=request.user)

        return render_to_response(
            'rdrf_cdes/patient_edit.html',
            context,
            context_instance=RequestContext(request))

    # def _get_index_context(self, registry_model, patient_model):
    #    #todo this probabably doesn't apply anymore in fhcontexts branch
    #    if registry_model.has_feature("family_linkage") and not patient_model.is_index and patient_model.active:
    #        return patient_model.my_index.default_context(registry_model)

    def create_patient_relatives(self, patient_relative_formset, patient_model, registry_model):
        if patient_relative_formset:
            patient_relative_formset.instance = patient_model
            patient_relative_models = patient_relative_formset.save()
            for patient_relative_model in patient_relative_models:
                patient_relative_model.patient = patient_model
                patient_relative_model.save()
                # explicitly synchronise with the patient that has already been created from
                # this patient relative ( if any )
                # to avoid infinite loops we are doing this explicitly in the views ( not overriding save)
                patient_relative_model.sync_relative_patient()

                tag = patient_relative_model.given_names + patient_relative_model.family_name
                # The patient relative form has a checkbox to "create a patient from the
                # relative"
                for form in patient_relative_formset:
                    if form.tag == tag:  # must be a better way to do this ...
                        if form.create_patient_flag:
                            logger.debug("creating patient from relative %s" %
                                         patient_relative_model)

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
            "place_of_birth",
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
            "next_of_kin_country",
            "next_of_kin_suburb",
            "next_of_kin_state",
            "next_of_kin_postcode",
            "next_of_kin_home_phone",
            "next_of_kin_mobile_phone",
            "next_of_kin_work_phone",
            "next_of_kin_email",
            "next_of_kin_parent_place_of_birth"
        ])

        rdrf_registry = (_("Registry"), [
            "rdrf_registry",
            "working_groups",
            "clinician"
        ])

        patient_address_section = (_("Patient Address"), None)

        # patient_consent_file_formset = inlineformset_factory(
        #     Patient, PatientConsent, form=PatientConsentFileForm, extra=0, can_delete=True, fields="__all__")
        # patient_consent_file_form = patient_consent_file_formset(
        #     instance=patient, prefix="patient_consent_file")
        #
        # patient_section_consent = patient_form.get_all_consent_section_info(
        #     patient, registry_code)
        # patient_section_consent_file = (_("Upload Consent File"), None)

        form_sections = [
            # (
            #     patient_form,
            #     patient_section_consent
            # ),
            # (
            #     patient_consent_file_form,
            #     (patient_section_consent_file,)
            # ),
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

    def _create_registry_specific_patient_form_class(self, user, form_class, registry_model, patient=None):
        additional_fields = OrderedDict()
        field_pairs = self._get_registry_specific_fields(user, registry_model)

        for cde, field_object in field_pairs:
            try:
                cde_policy = CdePolicy.objects.get(registry=registry_model, cde=cde)
                logger.debug("found a cde policy: %s" % cde_policy)
            except CdePolicy.DoesNotExist:
                cde_policy = None

            if cde_policy is None:
                additional_fields[cde.code] = field_object
            else:

                if user.is_superuser or cde_policy.is_allowed(user.groups.all(), patient):
                    # this is bad - registry specific fields in demographics are a bad idea
                    if patient.is_index:
                        additional_fields[cde.code] = field_object

        if len(additional_fields.keys()) == 0:
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
