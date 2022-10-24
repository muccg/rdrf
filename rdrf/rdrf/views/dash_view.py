from django.views.generic.base import View
from django.shortcuts import render
import logging

logger = logging.getLogger(__name__)
logger.debug("loading dash ...")
from dash import dcc, html
import dash
from django_plotly_dash import DjangoDash

from rdrf.models.definition.models import Registry
from rdrf.forms.dashboards import get_patients_dashboard_app


import plotly.express as px


class PatientsDashboardView(View):
    def get(self, request):
        logger.debug("in get request")
        context = {}
        registry_model = Registry.objects.get()

        app = DjangoDash("SimpleExample")  # replaces dash.Dash
        df = px.data.iris()  # iris is a pandas DataFrame
        fig = px.scatter(df, x="sepal_width", y="sepal_length")

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
                html.Div([dcc.Graph(figure=fig)], id="graph"),
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
