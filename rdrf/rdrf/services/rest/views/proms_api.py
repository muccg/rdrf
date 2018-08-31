from rest_framework.views import APIView
from rest_framework.response import Response
from rdrf.models.proms.models import Survey
from rdrf.models.proms.models import SurveyAssignment
from rdrf.models.proms.models import SurveyStates
from rdrf.models.definition.models import Registry


class SurveyEndpoint(APIView):
    def get(self, request):
        survey_id = int(request.GET.get("survey_id"))
        survey_model = Survey.objects.get(id=survey_id)
        return Response(survey_model.client_rep)

    def post(self, request):
        survey_id = request.POST.get("survey_id")
        patient_token = request.POST.get("patient_token")
        patient_data = request.POST.get("survey_response")

        survey_model = Survey.objects.get(id=survey_id)


        survey_assignment = SurveyAssignment.objects.get(registry=survey_model.registry,
                                                         survey_name=survey_model.name,
                                                         patient_token=patient_token,
                                                         state=SurveyStates.REQUESTED)
        
        
        survey_assignment.response = patient_data
        survey_assignment.state = SurveyStates.COMPLETED
        survey_assignment.save()
