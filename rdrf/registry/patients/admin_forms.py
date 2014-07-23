from django import forms
from registry.utils import get_static_url

from models import *


class PatientDoctorForm(forms.ModelForm):
    OPTIONS = (
        (1, "Primary Care"),
        (2, "Paediatric Neurologist"),
        (3, "Neurologist"),
        (4, "Geneticist"),
        (5, "Specialist - Other"),
    )
    relationship = forms.ChoiceField(label="Type of Medical Professional", choices=OPTIONS)

    class Meta:
        model = PatientDoctor


class PatientForm(forms.ModelForm):

    ADDRESS_ATTRS = {
        "rows": 3,
        "cols": 30,
    }

    consent = forms.BooleanField(required=True, help_text="The patient consents to be part of the registry and have data retained and shared in accordance with the information provided to them", label="Consent given")
    consent_clinical_trials = forms.BooleanField(required=False, help_text="The patient consents to be contacted about clinical trials or other studies related to their condition", label="Consent for clinical trials given")
    consent_sent_information = forms.BooleanField(required=False, help_text="The patient consents to be sent information on their condition", label="Consent for being sent information given")
    date_of_birth = forms.DateField(widget=forms.DateInput(attrs={'class':'datepicker'}, format='%d-%m-%Y'), help_text="DD-MM-YYYY", input_formats=['%d-%m-%Y'])
    date_of_migration = forms.DateField(widget=forms.DateInput(attrs={'class':'datepicker'}, format='%d-%m-%Y'), required=False, help_text="Date of migration (DD-MM-YYYY)", label="Migration", input_formats=['%d-%m-%Y'])
    address = forms.CharField(widget=forms.Textarea(attrs=ADDRESS_ATTRS))

    class Meta:
        model = Patient
        widgets = {
            'next_of_kin_address': forms.Textarea(attrs={"rows": 3,"cols": 30}),
            'inactive_reason': forms.Textarea(attrs={"rows": 3,"cols": 30}),
        }

    # Added to ensure unique (familyname, givennames, workinggroup)
    # Does not need a unique constraint on the DB

    def clean(self):
        cleaneddata = self.cleaned_data

        family_name = stripspaces(cleaneddata.get("family_name", "") or "").upper()
        given_names = stripspaces(cleaneddata.get("given_names", "") or "")

        # working_group can be None, which is annoying for the db query below
        # so working_group should be required, but how do we make it required in the model?
        # working_group = models.ForeignKey(groups.models.WorkingGroup)
        workinggroup = cleaneddata.get("working_group", "") or ""
        if not workinggroup:
            raise forms.ValidationError('The working group is required.')

        if self.instance:
            id = self.instance.pk
        else:
            id = None
        patients = Patient.objects.filter(family_name__iexact=family_name, given_names__iexact=given_names, working_group=workinggroup)

        exists = False
        if len(patients) > 0:
            if id == None: # creating a new patient and existing one in the DB already
                exists = True
            elif id != patients[0].pk: # modifying an existing patient, check if there is another patient with same names but different pk
                exists = True
        if exists:
            raise forms.ValidationError('There is already a patient with the same family and given names in this working group: "%s %s %s".' % (family_name, given_names, workinggroup))

        return super(PatientForm, self).clean()
