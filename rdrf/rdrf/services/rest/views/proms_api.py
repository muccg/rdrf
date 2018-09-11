from rest_framework.views import APIView
from rest_framework.response import Response
from rdrf.models.definition.models import Registry
from rdrf.models.proms.models import Survey
from rdrf.models.proms.models import SurveyAssignment
from rdrf.models.proms.models import SurveyStates
from rest_framework.decorators import permission_classes
from rest_framework import permissions
from django.views.generic.base import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.decorators import api_view
from django.shortcuts import render
from django.http import HttpResponseRedirect


import json

import logging
logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class SurveyEndpoint(View):

    def post(self, request):
        logger.debug("survey endpoint post")
        data = json.loads(request.body)
        patient_token = data.get("patient_token")
        logger.debug("patient_token = %s" % patient_token)
        survey_answers= data.get("answers")
        logger.debug("answers ditionary = %s" % survey_answers)
        registry_code = data.get("registry_code")
        logger.debug("registry code = %s" % registry_code)
        survey_name = data.get("survey_name")
        
        registry_model = Registry.objects.get(code=registry_code)
        

        survey_model = Survey.objects.get(registry=registry_model,
                                          name=survey_name)

        logger.debug("survey = %s" % survey_model)
        


        survey_assignment = SurveyAssignment.objects.get(registry=survey_model.registry,
                                                         survey_name=survey_model.name,
                                                         patient_token=patient_token,
                                                         state=SurveyStates.REQUESTED)
        
        
        survey_assignment.response = json.dumps(survey_answers)
        survey_assignment.state = SurveyStates.COMPLETED
        survey_assignment.save()
        return render(request, "proms/proms_completed.html",{})
