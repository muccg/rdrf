from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.views.generic.base import View
from rdrf.models.proms.models import SurveyAssignment
from rdrf.models.proms.models import Survey
from rdrf.models.proms.models import SurveyStates
from rdrf.models.definition.models import Registry
from django.http import HttpResponseRedirect
from django.http import Http404
from django.core.urlresolvers import reverse
from django.shortcuts import render
import json

import logging
logger = logging.getLogger(__name__)

class PromsCompletedPageView(View):
    def get(self, request):
        logger.debug("proms completed view")
        return render(request, "proms/proms_completed.html",{})
        

class PromsView(View):
    def get(self, request):
        logger.debug("proms view")
        patient_token = request.session.get("patient_token", None)
        logger.debug("patient_token = %s" % patient_token)
        if patient_token is None:
            raise Http404

        survey_assignment = self._get_survey_assignment(patient_token)
        if survey_assignment is None:
            raise Http404
        
        registry_model = survey_assignment.registry
        survey_name = survey_assignment.survey_name

        survey_model = get_object_or_404(Survey,
                                         registry=registry_model,
                                         name=survey_name)
        
        survey_questions = survey_model.client_rep

        completed_page = reverse("proms_completed")
        
        context = {"production": False,
                   "patient_token": patient_token,
                   "registry_code": registry_model.code,
                   "survey_name": survey_name,
                   "completed_page": completed_page,
                   "questions": json.dumps(survey_questions),
        }
        
        return render(request, "proms/proms.html", context)

    def _get_survey_assignment(self, patient_token):
        # patient tokens should be once off so unique to assignments
        try:
            return SurveyAssignment.objects.get(patient_token=patient_token)
        except SurveyAssignment.DoesNotExist:
            logger.error("No survey assignment with patient token %s" % patient_token)
            return None
        except SurveyAssignment.MultipleObjectsReturned:
            logger.error("Multiple survey assignments for patient token %s" % patient_token)
            return None

class PromsLandingPageView(View):
    def get(self, request):
        logger.debug("proms landing page")
        patient_token = request.GET.get("t",None)
        logger.debug("patient_token = %s" % patient_token)
        registry_code = request.GET.get("r", None)
        logger.debug("registry_code = %s" % registry_code)
        survey_name = request.GET.get("s", None)
        logger.debug("survey_name = %s" % survey_name)
        if not self._is_valid(patient_token,
                              registry_code,
                              survey_name):
            raise Http404

        logger.debug("valid")
        
        registry_model = get_object_or_404(Registry, code=registry_code)
        logger.debug("registry = %s" % registry_model)
        survey_model = get_object_or_404(Survey,
                                         registry=registry_model,
                                         name=survey_name)

        logger.debug("survey_model = %s" % survey_model)
        
        survey_assignment = get_object_or_404(SurveyAssignment,
                                              registry=registry_model,
                                              survey_name=survey_name,
                                              patient_token=patient_token,
                                              state=SurveyStates.REQUESTED)

        logger.debug("survey assignment = %s" % survey_assignment)

        survey_assignment.response = "{}";
        #survey_assignment.state = SurveyStates.STARTED
        survey_assignment.save()
        logger.debug("reset survey assignment")

        request.session["patient_token"] = patient_token
        logger.debug("patient_token set in session")
        logger.debug("redirecting to proms page")
                                          
        return HttpResponseRedirect(reverse("proms"))

    def _is_valid(self, patient_token, registry_code, survey_name):
        return True


        
        
                                               
            
        
        
