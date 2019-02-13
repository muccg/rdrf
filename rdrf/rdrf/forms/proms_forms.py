from django import forms

from rdrf.models.proms.models import SurveyRequest


class SurveyRequestForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        surveys = kwargs.get("surveys", [])
        del kwargs['surveys']
        super().__init__(*args, **kwargs)
        self.fields['survey_name'] = forms.ChoiceField(choices=surveys)

    class Meta:
        model = SurveyRequest
        fields = '__all__'
        widgets = {
            "registry": forms.HiddenInput(),
            "patient": forms.HiddenInput(),
            "response": forms.HiddenInput(),
            "user": forms.HiddenInput(),
            "state": forms.HiddenInput(),
            "patient_token": forms.HiddenInput(),
            "error_detail": forms.HiddenInput,
        }
