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

class PatientParentForm(forms.ModelForm):
    OPTIONS = (
        ("Mother", "Mother"),
        ("Father", "Father")
    )
    relationship = forms.ChoiceField(choices=OPTIONS)

    class Meta:
        model = PatientParent

class PatientForm(forms.ModelForm):

    ADDRESS_ATTRS = {
        "rows": 3,
        "cols": 30,
    }

    consent = forms.BooleanField(required=True, help_text="Consent must be given for the patient to be entered on the registry", label="Consent given")
    date_of_birth = forms.DateField()
    date_of_migration = forms.DateField(required=False, help_text="Date of migration", label="Migration")
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
