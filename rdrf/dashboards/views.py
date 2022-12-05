from datetime import datetime
from django.shortcuts import render
from django.shortcuts import get_object_or_404
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

import logging

logger = logging.getLogger(__name__)

login_required_method = method_decorator(login_required)


class DashboardLocation:
    ALL_PATIENTS = "A"
    SINGLE_PATIENT = "S"


def create_graphic(vis_config, data, patient):
    # patient is None for all patients graphics
    # contextual single patient components
    # should be supplied with the patient
    title = vis_config.title
    if vis_config.code == "pcf":
        return PatientsWhoCompletedForms(title, vis_config.config, data).graphic
    elif vis_config.code == "tofc":
        return TypesOfFormCompleted(title, vis_config.config, data).graphic
    elif vis_config.code == "cfc":
        return CombinedFieldComparison(title, vis_config.config, data).graphic
    elif vis_config.code == "cpr":
        return ChangesInPatientResponses(title, vis_config.config, data).graphic
    elif vis_config.code == "sgc":
        return ScaleGroupComparison(title, vis_config.config, data, patient).graphic
    else:
        logger.error(f"dashboard error - unknown visualisation {vis_config.code}")
        raise Exception(f"Unknown code: {vis_config.code}")


def all_patients_app(vis_configs, graphics_map):
    app = DjangoDash(
        "AllPatientsDashboardApp", external_stylesheets=[dbc.themes.BOOTSTRAP]
    )
    app.layout = dbc.Container(
        [
            dcc.Store(id="store"),
            dbc.Tabs(
                [
                    dbc.Tab(label=f"{vc.title}", tab_id=f"{vc.code}")
                    for vc in vis_configs
                ],
                id="tabs",
                active_tab=f"{vis_configs[0].code}",
            ),
            html.Div(id="tab-content", className="p-4"),
        ]
    )

    @app.callback(
        Output("tab-content", "children"),
        [Input("tabs", "active_tab")],
    )
    def render_tab_content(active_tab):
        if not active_tab:
            return "No tab selected"
        else:
            return graphics_map[active_tab]

    return app


def single_patient_app(vis_configs, graphics_map, patient):
    app = DjangoDash(
        "SinglePatientDashboardApp", external_stylesheets=[dbc.themes.BOOTSTRAP]
    )
    app.layout = dbc.Container(
        [
            dcc.Store(id="store"),
            dbc.Tabs(
                [
                    dbc.Tab(label=f"{vc.title}", tab_id=f"{vc.code}")
                    for vc in vis_configs
                ],
                id="tabs",
                active_tab=f"{vis_configs[0].code}",
            ),
            html.Div(id="tab-content", className="p-4"),
        ]
    )

    @app.callback(
        Output("tab-content", "children"),
        [Input("tabs", "active_tab")],
    )
    def render_tab_content(active_tab):
        if not active_tab:
            return "No tab selected"
        else:
            return graphics_map[active_tab]

    return app


def tabbed_app(registry, main_title, patient=None):
    data = get_data(registry, patient)
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
        return None

    graphics_map = {vc.code: create_graphic(vc, data, patient) for vc in vis_configs}

    if dashboard == DashboardLocation.ALL_PATIENTS:
        app = all_patients_app(vis_configs, graphics_map)
    else:

        app = single_patient_app(vis_configs, graphics_map, patient)

    return app


class PatientsDashboardView(View):
    @method_decorator(anonymous_not_allowed)
    @login_required_method
    def get(self, request):
        context = {}
        t1 = datetime.now()
        registry = Registry.objects.get()
        app = tabbed_app(registry, "Tabbed App")
        t2 = datetime.now()

        context["seconds"] = (t2 - t1).total_seconds
        context["location"] = "Patients Dashboard"

        return render(request, "rdrf_cdes/patients_dashboard.html", context)


class PatientDashboardView(View):
    @method_decorator(anonymous_not_allowed)
    @login_required_method
    def get(self, request, patient_id):
        logger.debug("in patient dashboard view")
        from registry.patients.models import Patient
        from rdrf.security.security_checks import security_check_user_patient

        patient = get_object_or_404(Patient, id=patient_id)
        security_check_user_patient(request.user, patient)

        context = {}
        t1 = datetime.now()
        registry = Registry.objects.get()
        logger.debug("creating DjangoDash app..")
        app = tabbed_app(registry, "Tabbed App Single", patient)
        if app is None:
            context["state"] = "bad"
        else:
            context["state"] = "good"
        t2 = datetime.now()

        context["seconds"] = (t2 - t1).total_seconds
        context["location"] = "Patient Dashboard"

        return render(request, "rdrf_cdes/patient_dashboard.html", context)
