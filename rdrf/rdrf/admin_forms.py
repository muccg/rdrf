from django.forms import ModelForm, SelectMultiple, ChoiceField
from rdrf.models.definition.models import RegistryForm, CommonDataElement, Section
from registry.patients.models import Patient
from rdrf.models.definition.models import EmailTemplate
from django.conf import settings


class RegistryFormAdminForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super(RegistryFormAdminForm, self).__init__(*args, **kwargs)
        if 'instance' in kwargs:
            instance = kwargs["instance"]
            if instance is not None:
                sections = Section.objects.filter(
                    code__in=kwargs['instance'].sections.split(","))
                cdes = []
                for section in sections:
                    cdes += section.get_elements()
                self.fields['complete_form_cdes'].queryset = CommonDataElement.objects.filter(
                    code__in=cdes)

    class Meta:
        model = RegistryForm
        fields = "__all__"
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


class EmailTemplateAdminForm(ModelForm):
    """
    This form introduced so we can parametrise the languages list from settings.
    If we do this on the model it causes a migration fail in the build.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field_choices = settings.LANGUAGES
        self.fields['language'] = ChoiceField(choices=field_choices)

    class Meta:
        fields = "__all__"
        model = EmailTemplate
