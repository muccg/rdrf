from django import forms
from registry.utils import get_static_url
from django_countries import countries
from models import *
from rdrf.widgets import CountryWidget, StateWidget
from rdrf.dynamic_data import DynamicDataWrapper
import pycountry
import logging
logger = logging.getLogger("registry_log")
from registry.patients.patient_widgets import PatientRelativeLinkWidget
from django.core.exceptions import ValidationError
from django.forms.util import ErrorList, ErrorDict
from django.forms.widgets import TextInput, DateInput
from rdrf.hooking import run_hooks
from registry.patients.models import Patient, PatientRelative
from django.forms.widgets import Select
from django.db import transaction
from registry.groups.models import CustomUser
from rdrf.models import ConsentSection
from rdrf.models import ConsentQuestion


class PatientDoctorForm(forms.ModelForm):
    OPTIONS = (
        (1, "GP ( Primary Care)"),
        (2, "Specialist ( Lipid)"),
        (3, "Primary Care"),
        (4, "Paediatric Neurologist"),
        (5, "Neurologist"),
        (6, "Geneticist"),
        (7, "Specialist - Other"),
    )
    relationship = forms.ChoiceField(label="Type of Medical Professional", choices=OPTIONS)

    class Meta:
        model = PatientDoctor


class PatientRelativeForm(forms.ModelForm):
    class Meta:
        model = PatientRelative
        date_of_birth = forms.DateField(widget=forms.DateInput(attrs={'class': 'datepicker', "style": "width:70px"}, format='%d-%m-%Y'), input_formats=['%d-%m-%Y'])
        widgets = {
            'relative_patient': PatientRelativeLinkWidget,
            'sex': Select(attrs={"style": "width:90px"}),
            'living_status': Select(attrs={"style": "width:100px"}),
            'date_of_birth': forms.DateInput(attrs={'class': 'datepicker', "style": "width:70px"}, format='%d-%m-%Y'),
        }

    def __init__(self, *args, **kwargs):
        self.create_patient_data = None
        super(PatientRelativeForm, self).__init__(*args, **kwargs)
        self.fields['date_of_birth'].input_formats = ['%d-%m-%Y']

    def full_clean(self):
        self._errors = ErrorDict()
        if not self.is_bound:  # Stop further processing.
            return
        self.cleaned_data = {}
        keys_to_update = []
        # check for 'on' checkbox value for patient relative checkbox ( which means create patient )\
        # this 'on' value from widget is replaced by the pk of the created patient
        for k in self.data.keys():
            if k.startswith("relatives-") and k.endswith("-relative_patient"):
                if self.data[k] == "on":  # checkbox  checked - create patient from this data
                    patient_relative_index = k.split("-")[1]
                    logger.debug("creating patient from relative %s" % patient_relative_index)
                    self.create_patient_data = self._get_patient_relative_data(patient_relative_index)
                    try:
                        with transaction.atomic():
                            patient = self._create_patient()
                    except ValidationError, verr:
                        logger.info("validation error: %s" % verr)
                        self.data[k] = None  # get rid of the 'on'
                        self._errors[k] = ErrorList([verr.message])
                        return
                    except Exception, ex:
                        logger.error("other error: %s" % ex)
                        self.data[k] = None
                        self._errors[k] = ErrorList([ex.message])
                        return

                    keys_to_update.append((k, patient))

        for k, patient_model in keys_to_update:
            if patient_model is not None:
                self.data[k] = str(patient_model.pk)

        super(PatientRelativeForm, self).full_clean()



    def _create_patient(self):
        # Create the patient corresponding to this relative
        if not self.create_patient_data:
            return None

        def grab_data(substring):
            for k in self.create_patient_data:
                if substring in k:
                    return self.create_patient_data[k]

        p = Patient()

        logger.debug("data to create relative patient from = %s" % self.create_patient_data)

        given_names = grab_data("given_names")
        family_name = grab_data("family_name")
        date_of_birth = grab_data("date_of_birth")
        sex = grab_data("sex")
        id_of_patient_relative = grab_data("id")
        logger.debug("PatientRelativeId = %s" % id_of_patient_relative)
        patient_relative_model = PatientRelative.objects.get(id=int(id_of_patient_relative))
        logger.debug("patient relative model = %s" % patient_relative_model)
        patient_whose_relative_this_is = patient_relative_model.patient
        logger.debug("patient whose relative this is = %s" % patient_whose_relative_this_is)

        if not all([given_names, family_name, date_of_birth]):
            raise ValidationError(" Not all data supplied for relative : Patient not created")

        logger.debug("setting values on created patient ...")
        p.given_names = grab_data("given_names")
        logger.debug("set given names")
        p.family_name = grab_data("family_name")
        logger.debug("set family name")
        logger.debug(" date of birth to save to patient = %s" % date_of_birth)
        p.date_of_birth = self._set_date_of_birth(date_of_birth)
        logger.debug("set date of birth")
        p.sex = sex
        p.consent = True  # need to work out how to handle this
        logger.debug("set consent")

        p.active = True
        logger.debug("set active")
        try:
            p.save()
        except Exception, ex:
            raise ValidationError("Could not create patient from relative: %s" % ex)

        logger.debug("attempting to set rdrf registry")
        p.rdrf_registry = [r for r in patient_whose_relative_this_is.rdrf_registry.all()]
        logger.debug("set rdrf_registry")
        p.working_groups = [wg for wg in patient_whose_relative_this_is.working_groups.all()]
        logger.debug("set working groups")
        p.save()
        logger.debug("saved created patient ok with pk = %s" % p.pk)
        run_hooks('patient_created_from_relative', p)
        logger.debug("ran hooks ok")
        return p

    def _set_date_of_birth(self, dob):
        #todo figure  out why the correct input format is not being respected - the field for dob on PatientRelative is in aus format already
        parts = dob.split("-")
        return "-".join([parts[2], parts[1], parts[0]])

    def _get_patient_relative_data(self, index):
        data = {}
        for k in self.data:
            if k.startswith("relatives-%s-" % index):
                data[k] = self.data[k]
        return data


class PatientAddressForm(forms.ModelForm):
    class Meta:
        model = PatientAddress
        fields = ('address_type', 'address', 'suburb', 'state', 'postcode', 'country')

    country = forms.ComboField(widget=CountryWidget(attrs={'default': 'AU', 'onChange': 'select_country(this);'}))
    state = forms.ComboField(widget=StateWidget(attrs={'default': 'AU-WA'}))


class PatientForm(forms.ModelForm):

    ADDRESS_ATTRS = {
        "rows": 3,
        "cols": 30,
    }

    def __init__(self, *args, **kwargs):
        clinicians = CustomUser.objects.all()
        self.custom_consents = []  # list of consent fields agreed to
        #self.orig_user = None

        if 'instance' in kwargs:
            instance = kwargs['instance']
            registry_specific_data = self._get_registry_specific_data(instance)
            logger.debug("registry specific data = %s" % registry_specific_data)
            initial_data = kwargs.get('initial', {})
            for reg_code in registry_specific_data:
                initial_data.update(registry_specific_data[reg_code])

            self._update_initial_consent_data(instance, initial_data)

            kwargs['initial'] = initial_data

            clinicians = CustomUser.objects.filter(registry__in=kwargs['instance'].rdrf_registry.all())

        super(PatientForm, self).__init__(*args, **kwargs)   # NB I have moved the constructor

        if 'instance' in kwargs:
            instance = kwargs['instance']
            self._add_custom_consent_fields(instance)

        clinicians_filtered = [c.id for c in clinicians if c.is_clinician]
        self.fields["clinician"].queryset = CustomUser.objects.filter(id__in=clinicians_filtered)

    def _get_registry_specific_data(self, patient_model):
        mongo_wrapper = DynamicDataWrapper(patient_model)
        return mongo_wrapper.load_registry_specific_data()

    def _update_initial_consent_data(self, patient_model, initial_data):
        data = patient_model.consent_questions_data
        for consent_field_key in data:
            initial_data[consent_field_key] = data[consent_field_key]
            logger.debug("set initial data for %s to %s" % (consent_field_key, data[consent_field_key]))

    #consent = forms.BooleanField(required=True, help_text="The patient consents to be part of the registry and have data retained and shared in accordance with the information provided to them", label="Consent given")
    #consent_clinical_trials = forms.BooleanField(required=False, help_text="The patient consents to be contacted about clinical trials or other studies related to their condition", label="Consent for clinical trials given")
    #consent_sent_information = forms.BooleanField(required=False, help_text="The patient consents to be sent information on their condition", label="Consent for being sent information given")
    #consent_provided_by_parent_guardian = forms.BooleanField(required=False, help_text="The parent/guardian of the patient has provided consent", label="Parent/Guardian consent provided on behalf of the patient")
    date_of_birth = forms.DateField(widget=forms.DateInput(attrs={'class': 'datepicker'}, format='%d-%m-%Y'), help_text="DD-MM-YYYY", input_formats=['%d-%m-%Y'])

    class Meta:
        model = Patient
        widgets = {
            'next_of_kin_address': forms.Textarea(attrs={"rows": 3, "cols": 30}),
            'inactive_reason': forms.Textarea(attrs={"rows": 3, "cols": 30}),
            'user': forms.HiddenInput()
        }
        exclude = ['doctors']

    # Added to ensure unique (familyname, givennames, workinggroup)
    # Does not need a unique constraint on the DB

    def clean(self):
        self.custom_consents = {}
        cleaneddata = self.cleaned_data

        for k in cleaneddata:
            if k.startswith("customconsent_"):
                self.custom_consents[k] = cleaneddata[k]

        for k in self.custom_consents:
            del cleaneddata[k]
            logger.debug("removed custom consent %s" % k)

        family_name = stripspaces(cleaneddata.get("family_name", "") or "").upper()
        given_names = stripspaces(cleaneddata.get("given_names", "") or "")

        if "working_groups" not in cleaneddata:
            raise forms.ValidationError("Patient must be assigned to a working group")
        if not cleaneddata["working_groups"]:
            raise forms.ValidationError("Patient must be assigned to a working group")

        self._check_working_groups(cleaneddata)

        return super(PatientForm, self).clean()

    def save(self,  commit=True):
        logger.debug("saving patient data")
        patient_model = super(PatientForm, self).save(commit=False)
        patient_model.active = True
        #patient_model.user = self.orig_user
        logger.debug("patient instance = %s" % patient_model)
        try:
            patient_registries = [r for r in patient_model.rdrf_registry.all()]
        except ValueError:
            # If patient just created line above was erroring
            patient_registries = []
        logger.debug("patient registries = %s" % patient_registries)

        logger.debug("persisting custom consents from form")
        logger.debug("There are %s custom consents" % len(self.custom_consents.keys()))
        
        patient_model.working_groups = [wg for wg in self.cleaned_data["working_groups"]]
        patient_model.rdrf_registry = [reg for reg in self.cleaned_data["rdrf_registry"]]
        patient_model.clinician = self.cleaned_data["clinician"]
        
        if "user" in self.cleaned_data:
            patient_model.user = self.cleaned_data["user"]
        
        if commit:
            patient_model.save()

        for consent_field in self.custom_consents:
            logger.debug("saving consent field %s ( value to save = %s)" % (consent_field, self.custom_consents[consent_field]))
            registry_model, consent_section_model, consent_question_model = self._get_consent_field_models(consent_field)
            if registry_model in patient_registries:
                logger.debug("saving consents for %s %s" % (registry_model, consent_section_model))
                # are we still applicable?! - maybe some field on patient changed which means not so any longer?
                if consent_section_model.applicable_to(patient_model):
                    logger.debug("%s is applicable to %s" % (consent_section_model, patient_model))
                    cv = patient_model.set_consent(consent_question_model, self.custom_consents[consent_field], commit)
                    logger.debug("set consent value ok : cv = %s" % cv)

        return patient_model

    def _get_consent_field_models(self, consent_field):
        logger.debug("getting consent field models for %s" % consent_field)
        _, reg_pk, sec_pk, q_pk = consent_field.split("_")

        registry_model = Registry.objects.get(pk=reg_pk)
        consent_section_model = ConsentSection.objects.get(pk=sec_pk)
        consent_question_model = ConsentQuestion.objects.get(pk=q_pk)

        return registry_model, consent_section_model, consent_question_model

    def _add_custom_consent_fields(self, patient_model):
        for registry_model in patient_model.rdrf_registry.all():
            for consent_section_model in registry_model.consent_sections.all():
                if consent_section_model.applicable_to(patient_model):
                    for consent_question_model in consent_section_model.questions.all().order_by("position"):
                        consent_field = consent_question_model.create_field()
                        field_key = consent_question_model.field_key
                        self.fields[field_key] = consent_field
                        logger.debug("added consent field %s = %s" % (field_key, consent_field))

    def get_all_consent_section_info(self, patient_model, registry_code):
        section_tuples = []
        registry_model = Registry.objects.get(code=registry_code)
        
        for consent_section_model in registry_model.consent_sections.all():
            if consent_section_model.applicable_to(patient_model):
                section_tuples.append(self.get_consent_section_info(registry_model, consent_section_model))
        return section_tuples

    def get_consent_section_info(self, registry_model, consent_section_model):
        # return something like this for custom consents
        #consent = ("Consent", [
        #     "consent",
        #     "consent_clinical_trials",
        #     "consent_sent_information",
        # ])


        questions = []

        for field in self.fields:
            if field.startswith("customconsent_"):
                parts = field.split("_")
                reg_pk = int(parts[1])
                if reg_pk == registry_model.pk:
                    consent_section_pk = int(parts[2])
                    if consent_section_pk == consent_section_model.pk:
                        consent_section_model = ConsentSection.objects.get(pk=consent_section_pk)
                        questions.append(field)

        return ("%s %s" % (registry_model.code.upper(), consent_section_model.section_label), questions)

    def _check_working_groups(self, cleaned_data):
        working_group_data = {}
        for working_group in cleaned_data["working_groups"]:
            if working_group.registry:
                if working_group.registry.code not in working_group_data:
                    working_group_data[working_group.registry.code] = [working_group]
                else:
                    working_group_data[working_group.registry.code].append(working_group)

        bad = []
        for reg_code in working_group_data:
            if len(working_group_data[reg_code]) > 1:
                bad.append(reg_code)

        if bad:
            bad_regs = [Registry.objects.get(code=reg_code).name for reg_code in bad]
            raise forms.ValidationError("Patient can only belong to one working group per registry. Patient is assigned to more than one working for %s" % ",".join(bad_regs))
