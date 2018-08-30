from rest_framework.views import APIView
from rest_framework.response import Response
from rdrf.models.proms.models import Survey


class SurveyEndpoint(APIView):
    def get(self, request, survey_id):
        survey_model = Survey.objects.get(id=survey_id)
        return Response(survey_model.client_rep)
