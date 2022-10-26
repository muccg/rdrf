from django.views.generic.base import View
from django.shortcuts import render
from dash import dcc, html
import dash
import logging
from django_plotly_dash import DjangoDash
import plotly.express as px
from django.contrib.auth.decorators import login_required
from rdrf.helpers.utils import anonymous_not_allowed
from django.utils.decorators import method_decorator

logger = logging.getLogger(__name__)
login_required_method = method_decorator(login_required)


class PatientsDashboardView(View):
    @method_decorator(anonymous_not_allowed)
    @login_required_method
    def get(self, request):
        context = {}
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
