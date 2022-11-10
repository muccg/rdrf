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

from .components.tofc import TypesOfFormCompleted

logger = logging.getLogger(__name__)
login_required_method = method_decorator(login_required)


def test_app():
    logger.debug("creating DashApp")
    app = DjangoDash("App")  # replaces dash.Dash
    logger.debug("created DashApp")
    df = px.data.iris()  # iris is a pandas DataFrame
    fig = px.scatter(df, x="sepal_width", y="sepal_length")
    logger.debug("created fig")
    app.layout = html.Div(
        [
            dcc.RadioItems(
                id="dropdown-color",
                options=[
                    {"label": c, "value": c.lower()} for c in ["Red", "Green", "Blue"]
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

    logger.debug("created layout")

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

    logger.debug("created callbacks")
    return app


def chart(title, id, figure):
    return html.Div([html.H2(title), dcc.Graph(figure=figure)], id=id)


def overall_app():
    from .data import RegistryDataFrame
    from .models import VisualisationConfig
    from rdrf.models.definition.models import Registry
    from datetime import datetime, timedelta

    registry = Registry.objects.get()
    vis_config = VisualisationConfig.objects.get(registry=registry, code="overall")

    rdf = RegistryDataFrame(registry, vis_config.config)

    date_end = datetime.now()
    date_start = date_end - timedelta(days=7)

    types_forms_completed_df = rdf.types_of_forms_completed(date_start)
    tof = TypesOfFormCompleted(types_forms_completed_df, date_start, date_end)

    app = DjangoDash("App")
    app.layout = html.Div(
        [html.H1("Overall Patients"), chart("Types of Forms Completed", "tof", tof.pie)]
    )

    return app


class PatientsDashboardView(View):
    @method_decorator(anonymous_not_allowed)
    @login_required_method
    def get(self, request):
        context = {}
        app = overall_app()
        logger.debug("view instantiated app")
        logger.debug("rendering template ...")

        return render(request, "rdrf_cdes/patients_dashboard.html", context)
