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
from rdrf.forms.components import RDRFContextLauncherComponent
from registry.patients.models import Patient
from rdrf.forms.components import RDRFPatientInfoComponent
from rdrf.forms.navigation.locators import PatientLocator
from rdrf.forms.proms_forms import SurveyRequestForm
from rdrf.models.proms.models import SurveyRequest
from rdrf.models.proms.models import SurveyRequestStates
from django.http import JsonResponse
import json
import qrcode


import logging
logger = logging.getLogger(__name__)

class PromsCompletedPageView(View):
    def get(self, request):
        logger.debug("proms completed view")
        return render(request, "proms/proms_completed.html", {})


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
        logger.debug("proms page GET")
        patient_token = request.GET.get("t", None)
        logger.debug("patient_token = %s" % patient_token)
        registry_code = request.GET.get("r", None)
        logger.debug("registry_code = %s" % registry_code)
        survey_name = request.GET.get("s", None)
        logger.debug("survey_name = %s" % survey_name)
        if not self._is_valid(patient_token,
                              registry_code,
                              survey_name):
            raise Http404

        registry_model = get_object_or_404(Registry, code=registry_code)
        logger.debug("registry = %s" % registry_model)
        survey_assignment = get_object_or_404(SurveyAssignment,
                                              patient_token=patient_token,
                                              state=SurveyStates.REQUESTED)
        survey_display_name = survey_assignment.survey.display_name
        preamble_text = registry_model.metadata.get("preamble_text")
        context = {
            "preamble_text": preamble_text,
            "survey_name": survey_display_name
        }
        return render(request, "proms/preamble.html", context)

    def _is_valid(self, patient_token, registry_code, survey_name):
        return True

    def post(self, request):
        logger.debug("proms landing page POST")
        patient_token = request.GET.get("t", None)
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
        logger.debug("registry metadata (preamble text)= %s" % registry_model.metadata.get("preamble_text"))

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
        survey_assignment.response = "{}"
        survey_assignment.save()
        logger.debug("reset survey assignment")
        request.session["patient_token"] = patient_token
        logger.debug("patient_token set in session")
        logger.debug("redirecting to proms page")
        return HttpResponseRedirect(reverse("proms"))

class PromsClinicalView(View):
    """
    What the clinical system sees
    """

    def get(self, request, registry_code, patient_id):
        registry_model = Registry.objects.get(code=registry_code)
        patient_model = Patient.objects.get(id=patient_id)

        context = self._build_context(request.user,
                                      registry_model,
                                      patient_model)

        return render(request, "proms/proms_clinical.html", context)

    def _build_context(self, user, registry_model, patient_model):
        survey_requests = self._get_survey_requests(registry_model,
                                                    patient_model)
        context_launcher = RDRFContextLauncherComponent(user,
                                                        registry_model,
                                                        patient_model,
                                                        "PROMS")

        survey_request_form = self._build_survey_request_form(registry_model,
                                                              patient_model,
                                                              user)

        context = {
            "context_launcher": context_launcher.html,
            "location": "Patient Reported Outcomes",
                        "patient": patient_model,
                        "survey_requests": survey_requests,
                        "patient_link": PatientLocator(registry_model,
                                                       patient_model).link,
                        "patient_info": RDRFPatientInfoComponent(registry_model, patient_model).html,
                        "survey_request_form": survey_request_form,

        }

        return context

    def _build_survey_request_form(self, registry_model, patient_model, user):
        initial_data = {
            "patient": patient_model,
            "registry": registry_model,
            "user": user.username,
        }
        # restrict the available survey choices based on the registry config

        surveys = [(s["code"], s["description"]) for s in registry_model.metadata.get("surveys", [])]

        return SurveyRequestForm(initial=initial_data, surveys=surveys)

    def _get_survey_requests(self, registry_model, patient_model):
        return SurveyRequest.objects.filter(registry=registry_model,
                                            patient=patient_model).order_by("-created").all()

    def post(self, request, registry_code, patient_id):
        survey_name = request.POST.get("survey_name")
        logger.debug("survey_name = %s" % survey_name)
        patient_id = request.POST.get("patient")
        logger.debug("patient_id = %s" % patient_id)
        registry_id = request.POST.get("registry")
        logger.debug("registry_id = %s" % registry_id)
        patient_token = request.POST.get("patient_token")
        logger.debug("patient_token = %s" % patient_token)
        user = request.POST.get("user")
        logger.debug("user = %s" % user)
        registry_model = Registry.objects.get(id=registry_id)
        logger.debug("got registry")
        patient_model = Patient.objects.get(id=patient_id)
        logger.debug("got patient")

        survey_request = SurveyRequest(registry=registry_model,
                                       patient=patient_model,
                                       user=user,
                                       state=SurveyRequestStates.REQUESTED,
                                       patient_token=patient_token)
        survey_request.save()
        logger.debug("saved survey request")

        logger.debug("sending request")
        survey_request.send()
        logger.debug("sent request to create survey assignment")

        return JsonResponse({"patient_token": survey_request.patient_token})


class PromsQRCodeImageView(View):
    def get(self, request, patient_token):
        from django.http import HttpResponse
        try:
            survey_request = SurveyRequest.objects.get(patient_token=patient_token)
        except SurveyRequest.DoesNotExist:
            raise Http404
        except SurveyRequest.MultipleObjectsReturned:
            raise Http404

        link = survey_request.email_link
        image = self._make_image(link)
        response = HttpResponse(content_type='image/png')
        image.save(response)
        return response

    def _make_image(self, data):
        return qrcode.make(data)
