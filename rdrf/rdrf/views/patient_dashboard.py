from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic.base import View
from django.shortcuts import render
from registry.patients.models import Patient
from rdrf.security.security_checks import security_check_user_patient

import logging

logger = logging.getLogger(__name__)


class PatientDashboardView(View):

    @method_decorator(login_required)
    def get(self, request, registry_code, patient_id):
        logger.info("PATIENTDASHBOARDGET %s %s %s" % (request.user,
                                                      registry_code,
                                                      patient_id))
        patient_model = Patient.objects.get(pk=patient_id)
        security_check_user_patient(request.user, patient_model)
        template_context = {}
        template_context["context_launcher"] = ""

        return render(request, 'rdrf_cdes/patient_dashboard.html', template_context)
