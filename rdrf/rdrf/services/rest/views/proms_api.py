from rest_framework.views import APIView
from rest_framework.response import Response
from rdrf.models.definition.models import Registry, RegistryForm, Section
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
from django.conf import settings
from rest_framework import status
from rdrf.services.rest.serializers import SurveyAssignmentSerializer
from rdrf.services.rest.auth import PromsAuthentication
from rest_framework.permissions import AllowAny
import requests
import json


import logging
logger = logging.getLogger(__name__)


def multicde(cde_model):
    datatype = cde_model.datatype.lower().strip()
    return datatype == "range" and cde_model.allow_multiple


@method_decorator(csrf_exempt, name='dispatch')
class SurveyEndpoint(View):

    def post(self, request):
        data = json.loads(request.body)
        patient_token = data.get("patient_token")
        survey_answers = data.get("answers")
        registry_code = data.get("registry_code")
        survey_name = data.get("survey_name")

        registry_model = Registry.objects.get(code=registry_code)

        survey_model = Survey.objects.get(registry=registry_model,
                                          name=survey_name)

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
        ser = SurveyAssignmentSerializer(data=request.data)
        # call is valid befoe save
        if ser.is_valid():
            ser.save()
            return Response({"status": "OK"}, status=status.HTTP_201_CREATED)
        else:
            logger.warning("serialiser is not valid: %s" % ser.errors)

        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)


class PromsDelete(APIView):
    authentication_classes = (PromsAuthentication,)
    permission_classes = (AllowAny,)

    @method_decorator(csrf_exempt)
    def post(self, request, format=None):
        registry_code = request.POST.get("registry_code")
        survey_ids = request.POST.getlist("survey_ids")
        self.get_queryset(registry_code, survey_ids).delete()
        logger.info(f"deleted {len(survey_ids)} completed surveys that were downloaded for {registry_code} registry")
        return Response("deleted")

    def get_queryset(self, registry_code, survey_ids):
        return SurveyAssignment.objects.filter(state="completed", registry__code=registry_code, id__in=survey_ids)


class PromsDownload(APIView):
    authentication_classes = (PromsAuthentication,)
    permission_classes = (AllowAny,)

    @method_decorator(csrf_exempt)
    def post(self, request, format=None):
        registry_code = request.POST.get("registry_code", "")
        completed_survey_assignments = self.get_queryset(registry_code)
        completed_surveys = SurveyAssignmentSerializer(completed_survey_assignments, many=True)
        response = Response(completed_surveys.data)
        logger.info(f"downloaded {len(completed_survey_assignments)} completed surveys that were downloaded for {registry_code} registry")
        return response

    def get_queryset(self, registry_code):
        # we order the survey by updated date so the last answered survey will overwrite previous answered survey
        # (in case there are multiple answers for the same survey/patient)
        return SurveyAssignment.objects.filter(state="completed", registry__code=registry_code).order_by('updated')


class PromsProcessor:
    # todo refactor other proms system actions to use this class
    def __init__(self, registry_model):
        self.registry_model = registry_model
        self.proms_url = registry_model.proms_system_url

    def download_proms(self):
        from django.conf import settings

        if not self.proms_url:
            raise Exception("Registry %s does not have an associated proms system" % self.registry_model)

        api = "/api/proms/v1/promsdownload"

        api_url = self.proms_url + api
        post_data = {'proms_secret_token': settings.PROMS_SECRET_TOKEN, 'registry_code': self.registry_model.code}
        response = requests.post(api_url, data=post_data)

        if response.status_code != 200:
            logger.warning(f"Error retrieving proms")
            raise Exception("Error retrieving proms")
        else:
            data = response.json()
            survey_ids = []
            patient_ids = set()
            for survey_response in data:
                patient_token = survey_response["patient_token"]
                survey_name = survey_response["survey_name"]
                survey_data = json.loads(survey_response["response"])

                # Sanity check: the survey registry must the same as the current registry
                if survey_response['registry_code'] != self.registry_model.code:
                    raise Exception(f"survey response registry code '{survey_response['registry_code']}' "
                                    f"not equal to pull_proms registry code '{self.registry_model.code}'")

                try:
                    survey_request = SurveyRequest.objects.get(patient_token=patient_token,
                                                               survey_name=survey_name,
                                                               state=SurveyRequestStates.REQUESTED,
                                                               registry__code=survey_response['registry_code'])
                except SurveyRequest.DoesNotExist:
                    logger.error("could not find survey request")
                    continue

                except SurveyRequest.MultipleObjectsReturned:
                    logger.error("too many survey requests")
                    continue

                # Remember the patient ids so we can later update the calculated field for this patient.
                patient_ids.add(survey_request.patient.id)

                self._update_proms_fields(survey_request, survey_data)

                # Store the survey id so we can delete it on the PROMS site once all surveys are downloaded.
                survey_ids.append(survey_response["id"])

            # All went well, we can now delete the downloaded surveys from the PROMS site.
            if len(survey_ids) > 0:
                delete_post_data = {**post_data, 'survey_ids': survey_ids}
                self.delete_registry_proms(delete_post_data)

            # Fix calculation for this registry.
            if patient_ids:
                from django.core.management import call_command
                call_command('update_calculated_fields', registry_code=self.registry_model.code, patient_id=patient_ids)

    def delete_registry_proms(self, post_data):
        api_delete = "/api/proms/v1/promsdelete"
        api_delete_url = self.proms_url + api_delete
        delete_response = requests.post(api_delete_url, data=post_data)
        if delete_response.status_code != 200:
            logger.warning(f"Error deleting proms for {self.registry_model.code} registry")
            raise Exception(f"Error deleting proms for {self.registry_model.code} registry")

    def _update_proms_fields(self, survey_request, survey_data):
        from rdrf.models.definition.models import RDRFContext
        # pokes downloaded proms into correct fields inside
        # clinical system
        context_model = None
        patient_model = survey_request.patient
        metadata = self.registry_model.metadata
        consent_exists = False
        if "consents" in metadata:
            consent_dict = metadata["consents"]
            consent_exists = True
        else:
            logger.warning("No Consent metadata exists")

        is_followup = survey_request.survey.is_followup
        context_form_group = survey_request.survey.context_form_group
        if context_form_group is None and self.registry_model.has_feature("contexts"):
            error_msg = "No Context Form Group selected on Survey %s" % survey_request.survey.name
            raise Exception(error_msg)

        if survey_request.survey.form:
            target_form_model = survey_request.survey.form
        else:
            target_form_model = None

        if is_followup:
            context_model = RDRFContext(registry=self.registry_model, context_form_group=context_form_group,
                                        content_object=patient_model, display_name="Follow Up")
            context_model.save()
        else:
            if self.registry_model.has_feature("contexts"):
                try:
                    context_model = RDRFContext.objects.get(registry=self.registry_model,
                                                            context_form_group=context_form_group,
                                                            object_id=patient_model.pk)

                    if target_form_model and target_form_model not in context_form_group.forms:
                        error_msg = "The target form %s is not in the form group %s" % (target_form_model.name,
                                                                                        context_form_group.name)
                        raise Exception(error_msg)
                except RDRFContext.DoesNotExist:
                    error_msg = "Cannot locate context for group %s patient %s" % (context_form_group,
                                                                                   getattr(patient_model, settings.LOG_PATIENT_FIELDNAME))
                    raise Exception(error_msg)
                except RDRFContext.MultipleObjectsReturned:
                    error_msg = "Expecting one context for group %s patient %s" % (context_form_group,
                                                                                   getattr(patient_model, settings.LOG_PATIENT_FIELDNAME))
                    raise Exception(error_msg)

            else:
                # we should just use the "default" context
                context_model = patient_model.default_context(self.registry_model)

        if context_model is None:
            raise Exception("cannot determine proms pull context for patient %s" % getattr(patient_model, settings.LOG_PATIENT_FIELDNAME))

        # Retrieve the cde_path
        cde_paths = {}
        for question in survey_request.survey.survey_questions.all():
            cde_paths = {**cde_paths, question.cde.code: question.cde_path}

        for cde_code, value in survey_data.items():
            try:
                cde_model = CommonDataElement.objects.get(code=cde_code)
            except CommonDataElement.DoesNotExist:
                logger.error("could not find cde %s" % cde_code)
                continue

            try:
                is_consent = False
                if consent_exists:
                    consent_question_code = consent_dict.get(cde_code, None)
                    if consent_question_code is not None:
                        self._update_consentvalue(patient_model, consent_question_code, value)
                        is_consent = True

                if not is_consent:
                    # Find the cde code in the survey questions and check existance of cde_path
                    if cde_code in cde_paths.keys() and cde_paths[cde_code]:
                        form_name, section_code = list(filter(None, cde_paths[cde_code].split("/")))
                        form_model = RegistryForm.objects.get(name=form_name, registry__code=self.registry_model.code)
                        section_model = Section.objects.get(code=section_code)
                    else:
                        # override target_form_model if cde_path exists
                        form_model, section_model = self._locate_cde(cde_model, context_model, target_form_model)
            except BaseException as e:
                import traceback
                trace_back = traceback.format_exc()
                message = str(e) + " | " + str(trace_back)
                logger.error(f"could not locate cde {cde_code}: {message}")
                # should fail for now skip

                continue

            try:
                if not self.registry_model.has_feature("contexts"):
                    context_arg = None
                else:
                    context_arg = context_model

                if not is_consent:
                    patient_model.set_form_value(self.registry_model.code,
                                                 form_model.name,
                                                 section_model.code,
                                                 cde_model.code,
                                                 value,
                                                 context_arg)
            except Exception as ex:
                logger.error("Error updating proms field %s->%s: %s" % (cde_code,
                                                                        value,
                                                                        ex))
                continue

        survey_request.state = SurveyRequestStates.RECEIVED
        survey_request.response = json.dumps(survey_data)
        survey_request.save()

    def _update_consentvalue(self, patient_model, consent_code, answer):
        from rdrf.models.definition.models import ConsentQuestion
        consent_question_model = ConsentQuestion.objects.get(code=consent_code)
        patient_model.set_consent(consent_question_model, answer)

    def _locate_cde(self, target_cde_model, context_model, target_form_model):
        # retrieve first available..
        if target_form_model:
            form_models = [target_form_model]
        elif context_model.context_form_group:
            form_models = context_model.context_form_group.forms
        else:
            form_models = self.registry_model.forms

        for form_model in form_models:
            for section_model in form_model.section_models:
                if not section_model.allow_multiple:
                    for cde_model in section_model.cde_models:
                        if cde_model.code == target_cde_model.code:
                            return form_model, section_model
