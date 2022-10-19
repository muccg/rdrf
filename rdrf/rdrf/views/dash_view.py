from django.views.generic.base import View
from django.shortcuts import render
import logging

logger = logging.getLogger(__name__)
logger.debug("loading dash ...")
from dash import dcc, html
import dash
from django_plotly_dash import DjangoDash

logger.debug("loaded dash module")


class PatientsDashboardView(View):
    def get(self, request):
        logger.debug("in get request")
        context = {}
        logger.debug("patientsdashboard view")
        app = DjangoDash("SimpleExample")  # replaces dash.Dash

        app.layout = html.Div(
            [
                dcc.RadioItems(
                    id="dropdown-color",
                    options=[
                        {"label": c, "value": c.lower()}
                        for c in ["Red", "Green", "Blue"]
                    ],
                    value="red",
                ),
                html.Div(id="output-color"),
                dcc.RadioItems(
                    id="dropdown-size",
                    options=[
                        {"label": i, "value": j}
                        for i, j in [("L", "large"), ("M", "medium"), ("S", "small")]
                    ],
                    value="medium",
                ),
                html.Div(id="output-size"),
            ]
        )

        @app.callback(
            dash.dependencies.Output("output-color", "children"),
            [dash.dependencies.Input("dropdown-color", "value")],
        )
        def callback_color(dropdown_value):
            return "The selected color is %s." % dropdown_value

        @app.callback(
            dash.dependencies.Output("output-size", "children"),
            [
                dash.dependencies.Input("dropdown-color", "value"),
                dash.dependencies.Input("dropdown-size", "value"),
            ],
        )
        def callback_size(dropdown_color, dropdown_size):
            return "The chosen T-shirt is a %s %s one." % (
                dropdown_size,
                dropdown_color,
            )

        return render(request, "rdrf_cdes/patients_dashboard.html", context)
