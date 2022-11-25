from datetime import datetime
from django.shortcuts import render
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

from .models import VisualisationConfig

import logging

logger = logging.getLogger(__name__)

login_required_method = method_decorator(login_required)


def create_graphic(vis_config, data):
    title = vis_config.title
    if vis_config.code == "pcf":
        return PatientsWhoCompletedForms(title, vis_config.config, data).graphic
    elif vis_config.code == "tofc":
        return TypesOfFormCompleted(title, vis_config.config, data).graphic
    elif vis_config.code == "cfc":
        return CombinedFieldComparison(title, vis_config.config, data).graphic
    elif vis_config.code == "cpr":
        return ChangesInPatientResponses(title, vis_config.config, data).graphic
    else:
        logger.error(f"dashboard error - unknown visualisation {vis_config.code}")
        raise Exception(f"Unknown code: {vis_config.code}")


def tabbed_app(registry, main_title):
    data = get_data(registry)
    vis_configs = [
        vc
        for vc in VisualisationConfig.objects.filter(registry=registry).order_by(
            "position"
        )
    ]

    graphics_map = {vc.code: create_graphic(vc, data) for vc in vis_configs}

    app = DjangoDash("App", external_stylesheets=[dbc.themes.BOOTSTRAP])
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


class PatientsDashboardView(View):
    @method_decorator(anonymous_not_allowed)
    @login_required_method
    def get(self, request):
        context = {}
        t1 = datetime.now()
        registry = Registry.objects.get()
        _ = tabbed_app(registry, "Tabbed App")
        t2 = datetime.now()

        context["seconds"] = (t2 - t1).total_seconds
        context["location"] = "Patients Dashboard"

        return render(request, "rdrf_cdes/patients_dashboard.html", context)
