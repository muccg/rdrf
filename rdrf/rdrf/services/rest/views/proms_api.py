from rest_framework.views import APIView
from rest_framework.response import Response
from rdrf.models.proms.models import Survey
from rdrf.models.proms.models import SurveyAssignment
from rdrf.models.proms.models import SurveyStates

import logging
logger = logging.getLogger(__name__)

class SurveyEndpoint(APIView):
    def get(self, request):
        logger.debug("survey endpoint get")
        survey_id = int(request.GET.get("survey_id"))
        logger.debug("survey id = %s" % survey_id)
        survey_model = Survey.objects.get(id=survey_id)
        logger.debug("survey = %s" % survey)
        client_rep = survey_model.client_rep
        logger.debug("client_rep = %s" % client_rep)
        return Response(client_rep)

    def post(self, request):
        logger.debug("survey endpoint post")
        survey_id = request.POST.get("survey_id")
        logger.debug("survey id = %s" % survey_id)
        patient_token = request.POST.get("patient_token")
        logger.debug("patient_token = %s" % patient_token)
        patient_data = request.POST.get("survey_response")

        survey_model = Survey.objects.get(id=survey_id)


        survey_assignment = SurveyAssignment.objects.get(registry=survey_model.registry,
                                                         survey_name=survey_model.name,
                                                         patient_token=patient_token,
                                                         state=SurveyStates.REQUESTED)
        
        
        survey_assignment.response = patient_data
        survey_assignment.state = SurveyStates.COMPLETED
        survey_assignment.save()
