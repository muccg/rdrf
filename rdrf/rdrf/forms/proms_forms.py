from django.forms import ModelForm
from rdrf.models.proms.models import SurveyRequest

class SurveyRequestForm(ModelForm):
    class Meta:
        model = SurveyRequest
        fields = "__all__"
