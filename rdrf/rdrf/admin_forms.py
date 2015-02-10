from django.forms import ModelForm, CheckboxSelectMultiple, SelectMultiple

from models import RegistryForm, CommonDataElement, Section


class RegistryFormAdminForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super(RegistryFormAdminForm, self).__init__(*args, **kwargs)
        sections = Section.objects.filter(code__in=kwargs['instance'].sections.split(","))
        cdes = []
        for section in sections:
            cdes += section.get_elements()
        self.fields['complete_form_cdes'].queryset = CommonDataElement.objects.filter(code__in=cdes)

    class Meta:
        model = RegistryForm
        widgets= {
            'complete_form_cdes': SelectMultiple(attrs={'size': 20, 'style': 'width:50%'})
        }