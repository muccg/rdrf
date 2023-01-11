from datetime import datetime
from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.views.generic.base import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django_plotly_dash import DjangoDash
import dash_bootstrap_components as dbc
from dash import Input, Output, dcc, html

from rdrf.models.definition.models import Registry
from rdrf.helpers.utils import anonymous_not_allowed

from .data import get_data
from .components.pcf import PatientsWhoCompletedForms
from .components.tofc import TypesOfFormCompleted
from .components.cpr import ChangesInPatientResponses
from .components.cfc import CombinedFieldComparison
from .components.sgc import ScaleGroupComparison

from .models import VisualisationConfig
from .utils import needs_all_patients_data

from registry.patients.models import Patient

import logging

logger = logging.getLogger(__name__)

login_required_method = method_decorator(login_required)


class DashboardLocation:
    ALL_PATIENTS = "A"
    SINGLE_PATIENT = "S"


def create_graphic(vis_config, data, patient, all_patients_data=None):
    # patient is None for all patients graphics
    # contextual single patient components
    # should be supplied with the patient
    # all_patients_data is supplied only to Scale group Comparisons
    # that
    title = vis_config.title
    if vis_config.code == "pcf":
        return PatientsWhoCompletedForms(title, vis_config, data).graphic
    elif vis_config.code == "tofc":
        return TypesOfFormCompleted(title, vis_config, data).graphic
    elif vis_config.code == "cfc":
        return CombinedFieldComparison(title, vis_config, data).graphic
    elif vis_config.code == "cpr":
        return ChangesInPatientResponses(title, vis_config, data).graphic
    elif vis_config.code == "sgc":
        return ScaleGroupComparison(
            title, vis_config, data, patient, all_patients_data
        ).graphic
    else:
        logger.error(f"dashboard error - unknown visualisation {vis_config.code}")
        raise Exception(f"Unknown code: {vis_config.code}")


def tabbed_app(user, registry, main_title, patient=None):
    try:
        t1 = datetime.now()
        data = get_data(registry, patient)
        t2 = datetime.now()
        if patient is None:
            s = "all patients'"
        else:
            s = "one patient's"

        num_patients = Patient.objects.all().count()
        logger.info(
            f"time to get data for dashboard {main_title} ( {num_patients} patients )  = {(t2-t1).total_seconds()} seconds"
        )

    except ValueError:
        return None

    dashboard = (
        DashboardLocation.ALL_PATIENTS
        if patient is None
        else DashboardLocation.SINGLE_PATIENT
    )
    vis_configs = [
        vc
        for vc in VisualisationConfig.objects.filter(
            registry=registry, dashboard=dashboard
        ).order_by("position")
    ]

    if not vis_configs:
        logger.info("No visualisation configs. Won't create dashboard")
        return None

    if dashboard == DashboardLocation.SINGLE_PATIENT and needs_all_patients_data(
        vis_configs
    ):
        logger.info("getting all patients data for dashboard..")
        t1 = datetime.now()
        all_patients_data = get_data(registry, None)
        t2 = datetime.now()
        logger.info(
            f"time to get all patients data = {(t2-t1).total_seconds()} seconds"
        )
    else:
        all_patients_data = None

    graphics_map = {
        f"tab_{vc.id}": create_graphic(vc, data, patient, all_patients_data)
        for vc in vis_configs
    }

    if dashboard == DashboardLocation.ALL_PATIENTS:
        app = all_patients_app(vis_configs, graphics_map)
    else:
        app = single_patient_app(user, vis_configs, graphics_map, patient)

    return app


class PatientsDashboardView(View):
    @method_decorator(anonymous_not_allowed)
    @login_required_method
    def get(self, request):
        logger.debug("in patients dashboard view")
        t1 = datetime.now()
        registry = get_object_or_404(Registry)
        if not registry.has_feature("patient_dashboard"):
            raise Http404

        # app = tabbed_app(user, registry, "Tabbed App")
        t2 = datetime.now()

        context = {}
        context["seconds"] = (t2 - t1).total_seconds
        context["location"] = "Patients Dashboard"

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
