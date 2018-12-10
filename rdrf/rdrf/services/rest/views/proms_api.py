from rest_framework.views import APIView
from rest_framework.response import Response
from rdrf.models.definition.models import Registry
from rdrf.models.definition.models import CommonDataElement
from rdrf.models.proms.models import Survey
from rdrf.models.proms.models import SurveyAssignment
from rdrf.models.proms.models import SurveyRequest
from rdrf.models.proms.models import SurveyRequestStates
from rdrf.models.proms.models import SurveyStates
from django.views.generic.base import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import render
from rest_framework import status
from rdrf.services.rest.serializers import SurveyAssignmentSerializer
from rdrf.services.rest.auth import PromsAuthentication
from rest_framework.permissions import AllowAny
import requests
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
        return render(request, "proms/proms_completed.html", {})

class SurveyAssignments(APIView):
    queryset = SurveyAssignment.objects.all()
    authentication_classes = (PromsAuthentication,)
    permission_classes = (AllowAny,)

    @method_decorator(csrf_exempt)
    def post(self, request, format=None):
        logger.info("in survey assignments on proms system")
        ser = SurveyAssignmentSerializer(data=request.data)
        # call is valid befoe save
        if ser.is_valid():
            ser.save()
            logger.debug("ser saved ok")
            return Response({"status": "OK"}, status=status.HTTP_201_CREATED)
        else:
            logger.debug("serialiser is not valid: %s" % ser.errors)

        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)


class PromsDownload(APIView):
    authentication_classes = (PromsAuthentication,)
    permission_classes = (AllowAny,)

    @method_decorator(csrf_exempt)
    def post(self, request, format=None):
        logger.debug("received download request ...")
        completed_surveys = SurveyAssignmentSerializer(self.get_queryset(), many=True)
        response = Response(completed_surveys.data)
        logger.debug("serialised surveys")
        self.get_queryset().delete()
        logger.debug("deleted completed surveys that were downloaded")
        return response

    def get_queryset(self):
        return SurveyAssignment.objects.filter(state="completed")


class PromsProcessor:
    # todo refactor other proms system actions to use this class
    def __init__(self, registry_model):
        self.registry_model = registry_model
        self.proms_url = registry_model.proms_system_url

    def download_proms(self):
        from django.conf import settings

        if not self.proms_url:
            raise Exception("Registry %s does not have an associated proms system" % self.registry_model)

        logger.debug("downloading proms from proms system")

        api = "/api/proms/v1/promsdownload"

        api_url = self.proms_url + api
        headers = {'PROMS_SECRET_TOKEN': settings.PROMS_SECRET_TOKEN}
        logger.debug("making request to %s" % api_url)

        response = requests.post(api_url,
                                 headers=headers)

        if response.status_code != 200:
            raise Exception("Error retrieving proms")
        else:
            logger.debug("got proms data from proms system OK")
            data = response.json()
            logger.debug("There are %s surveys" % len(data))
            for survey_response in data:
                patient_token = survey_response["patient_token"]
                logger.debug("patient token = %s" % patient_token)
                survey_name = survey_response["survey_name"]
                logger.debug("survey_name = %s" % survey_name)
                logger.debug("survey response = %s" % survey_response)
                survey_data = json.loads(survey_response["response"])
                logger.debug("survey data = %s" % survey_data)
                try:
                    survey_request = SurveyRequest.objects.get(patient_token=patient_token,
                                                               survey_name=survey_name,
                                                               state=SurveyRequestStates.REQUESTED,
                                                               registry=self.registry_model)
                except SurveyRequest.DoesNotExist:
                    logger.error("could find survey request")
                    continue

                except SurveyRequest.MultipleObjectsReturned:
                    logger.error("too many survey requests")
                    continue

                logger.debug("matched survey request %s" % survey_request.pk)

                self._update_proms_fields(survey_request, survey_data)

    def _update_proms_fields(self, survey_request, survey_data):
        # pokes downloaded proms into correct fields inside
        # clinical system
        logger.debug("updating downloaded proms for survey request %s" % survey_request.pk)
        patient_model = survey_request.patient
        metadata = self.registry_model.metadata
        if "consents" in metadata:
            consent_dict = metadata["consents"]    
            logger.debug("Consents Codes %s" % consent_dict)

        for cde_code, value in survey_data.items():
            try:
                cde_model = CommonDataElement.objects.get(code=cde_code)
            except CommonDataElement.DoesNotExist:
                logger.error("could not find cde %s" % cde_code)
                continue

            # NB. this assumes cde  is unique across reg ...
            try:
                is_consent = False
                logger.debug("cde code  = %s" % cde_code)
                consent_question_code = consent_dict.get(cde_code, None)
                logger.debug("Consent Question Code X %s" % consent_question_code)
                if consent_question_code is not None:
                     consent_code = consent_dict[cde_code]
                     logger.debug("Consent Question Code X %s" % consent_code)
                     self._update_consentvalue(patient_model, consent_code, value)
                     is_consent = True

                if not is_consent:
                    form_model, section_model = self._locate_cde(cde_model)
            except BaseException:
                logger.error("could not locate cde %s" % cde_code)
                # should fail for now skip

                continue

            try:
                patient_model.set_form_value(self.registry_model.code,
                                             form_model.name,
                                             section_model.code,
                                             cde_model.code,
                                             value)
            except Exception as ex:
                logger.error("Error updating proms field %s->%s: %s" % (cde_code,
                                                                        value,
                                                                        ex))
                continue

            logger.debug("proms updated! %s %s %s %s --> %s" % (patient_model,
                                                                form_model.name,
                                                                section_model.code,
                                                                cde_model.code,
                                                                value))

        survey_request.state = SurveyRequestStates.RECEIVED
        survey_request.response = json.dumps(survey_data)
        survey_request.save()
        logger.debug("updated survey_request state to received")

    def _update_consentvalue(self, patient_model, consent_code, answer):
        from rdrf.models.definition.models import ConsentQuestion
        logger.debug("Answer to save %s" % answer)
        consent_question_model = ConsentQuestion.objects.get(code=consent_code)
        patient_model.set_consent(consent_question_model, answer)

    def _locate_cde(self, target_cde_model):
        # retrieve first available..
        for form_model in self.registry_model.forms:
            for section_model in form_model.section_models:
                if not section_model.allow_multiple:
                    for cde_model in section_model.cde_models:
                        if cde_model.code == target_cde_model.code:
                            return form_model, section_model
