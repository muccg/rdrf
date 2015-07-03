from django.forms import ModelForm, SelectMultiple, ChoiceField
from models import RegistryForm, CommonDataElement, Section
from registry.patients.models import Patient


class RegistryFormAdminForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super(RegistryFormAdminForm, self).__init__(*args, **kwargs)
        if 'instance' in kwargs:
            sections = Section.objects.filter(code__in=kwargs['instance'].sections.split(","))
            cdes = []
            for section in sections:
                cdes += section.get_elements()
            self.fields['complete_form_cdes'].queryset = CommonDataElement.objects.filter(code__in=cdes)

    class Meta:
        model = RegistryForm
        widgets = {
            'complete_form_cdes': SelectMultiple(attrs={'size': 20, 'style': 'width:50%'})
        }


class DemographicFieldsAdminForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super(DemographicFieldsAdminForm, self).__init__(*args, **kwargs)

        patient_fields = Patient._meta.fields
        field_choices = []
        for patient_field in patient_fields:
            field_choices.append((patient_field.name, patient_field.name))

        field_choices.sort()
        self.fields['field'] = ChoiceField(choices=field_choices)
