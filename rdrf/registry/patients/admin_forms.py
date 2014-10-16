from django import forms
from registry.utils import get_static_url
from django_countries import countries
from models import *
from rdrf.widgets import CountryWidget, StateWidget
from rdrf.dynamic_data import DynamicDataWrapper
import pycountry
import logging
logger = logging.getLogger("registry_log")


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


class PatientAddressForm(forms.ModelForm):
    class Meta:
        model = PatientAddress
        
        fields = ('address_type', 'address', 'country', 'state', 'suburb', 'postcode')

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
            registry_specific_data = self._get_registry_specific_data(instance)
            initial_data = kwargs.get('initial', {})
            for reg_code in registry_specific_data:
                initial_data.update(registry_specific_data[reg_code])
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
