from datetime import datetime
from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.views.generic.base import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from rdrf.models.definition.models import Registry
from rdrf.helpers.utils import anonymous_not_allowed

import logging

logger = logging.getLogger(__name__)

login_required_method = method_decorator(login_required)


class PatientsDashboardView(View):
    @method_decorator(anonymous_not_allowed)
    @login_required_method
    def get(self, request):
        logger.debug("in patients dashboard view")
        t1 = datetime.now()
        registry = get_object_or_404(Registry)
        if not registry.has_feature("patient_dashboard"):
            raise Http404

        t2 = datetime.now()

        context = {}
        context["seconds"] = (t2 - t1).total_seconds
        context["location"] = "All Patients Dashboard"

        logger.debug("rendering all patients dashboard")

        return render(request, "rdrf_cdes/patients_dashboard.html", context)


class PatientDashboardView(View):
    @method_decorator(anonymous_not_allowed)
    @login_required_method
    def get(self, request, patient_id):
        from registry.patients.models import Patient
        from rdrf.security.security_checks import security_check_user_patient

        patient = get_object_or_404(Patient, id=patient_id)
        security_check_user_patient(request.user, patient)

        context = {}
        t1 = datetime.now()

        registry = get_object_or_404(Registry)

        if not registry.has_feature("patient_dashboard"):
            raise Http404

        session = request.session

        dash_context = request.session.get("django_plotly_dash", dict())
        dash_context["patient_id"] = patient_id
        session["django_plotly_dash"] = dash_context
        context["state"] = "good"
        t2 = datetime.now()

        context["seconds"] = (t2 - t1).total_seconds
        context["location"] = "Patient Dashboard"

        return render(request, "rdrf_cdes/patient_dashboard.html", context)
