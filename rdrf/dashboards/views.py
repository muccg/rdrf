from datetime import datetime
from django.shortcuts import render
from django.views.generic.base import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from dash import html
from django_plotly_dash import DjangoDash
import dash_bootstrap_components as dbc

from rdrf.models.definition.models import Registry
from rdrf.helpers.utils import anonymous_not_allowed

from .data import get_data
from .components.pcf import PatientsWhoCompletedForms
from .components.tofc import TypesOfFormCompleted
from .components.cpr import ChangesInPatientResponses
from .models import VisualisationConfig

import logging

logger = logging.getLogger(__name__)

login_required_method = method_decorator(login_required)


def create_graphic(vis_config, data):
    if vis_config.code == "pcf":
        return PatientsWhoCompletedForms(vis_config.config, data).graphic
    elif vis_config.code == "tofc":
        return TypesOfFormCompleted(vis_config.config, data).graphic
    elif vis_config.code == "fgc":
        return None
        # return FieldGroupComparison(vis_config.config, data).graphic
    elif vis_config.code == "cpr":
        return ChangesInPatientResponses(vis_config.config, data).graphic
    else:
        logger.error(f"dashboard error - unknown visualisation {vis_config.code}")
        raise Exception(f"Unknown code: {vis_config.code}")


def all_patients_app():

    registry = Registry.objects.get()
    app = DjangoDash("App", external_stylesheets=[dbc.themes.BOOTSTRAP])

    graphics = []

    t1 = datetime.now()

    data = get_data(registry)

    for vis_config in VisualisationConfig.objects.filter(
        registry=registry, dashboard="A"
    ):

        try:
            logger.debug(f"creating graphic {vis_config.code}")
            graphic = create_graphic(vis_config, data)
        except Exception as ex:
            code = vis_config.code
            logger.error(f"Error creating graphic {code}: {ex}")
            graphic = None

        if graphic is not None:
            graphics.append(graphic)

    app.layout = html.Div(graphics, id="allpatientsdashboard")
    t2 = datetime.now()
    return app, (t2 - t1).total_seconds()


class PatientsDashboardView(View):
    @method_decorator(anonymous_not_allowed)
    @login_required_method
    def get(self, request):
        context = {}
        app, secs = all_patients_app()
        logger.debug("view instantiated app")
        logger.debug("rendering template ...")

        context["seconds"] = secs

        return render(request, "rdrf_cdes/patients_dashboard.html", context)
