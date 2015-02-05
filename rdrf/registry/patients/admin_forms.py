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
        if 'instance' in kwargs:
            instance = kwargs['instance']
            #registry_specific_data = self._get_registry_specific_data(instance)
            #logger.debug("registry specific data = %s" % registry_specific_data)
            initial_data = kwargs.get('initial', {})
            # for reg_code in registry_specific_data:
            #     initial_data.update(registry_specific_data[reg_code])
            kwargs['initial'] = initial_data

        super(PatientForm, self).__init__(*args, **kwargs)

    def _get_registry_specific_data(self, patient_model):
        mongo_wrapper = DynamicDataWrapper(patient_model)
        return mongo_wrapper.load_registry_specific_data()

    consent = forms.BooleanField(required=True, help_text="The patient consents to be part of the registry and have data retained and shared in accordance with the information provided to them", label="Consent given")
    consent_clinical_trials = forms.BooleanField(required=False, help_text="The patient consents to be contacted about clinical trials or other studies related to their condition", label="Consent for clinical trials given")
    consent_sent_information = forms.BooleanField(required=False, help_text="The patient consents to be sent information on their condition", label="Consent for being sent information given")
    date_of_birth = forms.DateField(widget=forms.DateInput(attrs={'class': 'datepicker'}, format='%d-%m-%Y'), help_text="DD-MM-YYYY", input_formats=['%d-%m-%Y'])

    class Meta:
        model = Patient
        widgets = {
            'next_of_kin_address': forms.Textarea(attrs={"rows": 3, "cols": 30}),
            'inactive_reason': forms.Textarea(attrs={"rows": 3, "cols": 30}),
        }

    # Added to ensure unique (familyname, givennames, workinggroup)
    # Does not need a unique constraint on the DB

    def clean(self):
        cleaneddata = self.cleaned_data

        family_name = stripspaces(cleaneddata.get("family_name", "") or "").upper()
        given_names = stripspaces(cleaneddata.get("given_names", "") or "")

        if "working_groups" not in cleaneddata:
            raise forms.ValidationError("Patient must be assigned to a working group")
        if not cleaneddata["working_groups"]:
            raise forms.ValidationError("Patient must be assigned to a working group")

        self._check_working_groups(cleaneddata)

        return super(PatientForm, self).clean()

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
