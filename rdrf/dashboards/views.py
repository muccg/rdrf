from datetime import datetime, timedelta
from django.shortcuts import render
from django.views.generic.base import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from dash import dcc, html
import dash
from django_plotly_dash import DjangoDash
import dash_bootstrap_components as dbc
import plotly.express as px

from rdrf.models.definition.models import Registry
from rdrf.helpers.utils import anonymous_not_allowed

from .data import RegistryDataFrame
from .data import get_data
from .components.common import card, chart
from .components.pcf import PatientsWhoCompletedForms
from .components.fgc import FieldGroupComparison
from .components.tofc import TypesOfFormCompleted
from .models import VisualisationConfig

import logging

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


def overall_app():
    from .data import RegistryDataFrame
    from .models import VisualisationConfig
    from rdrf.models.definition.models import Registry
    from datetime import datetime, timedelta

    t1 = datetime.now()

    registry = Registry.objects.get()

    vis_config = VisualisationConfig.objects.get(registry=registry, code="overall")

    rdf = RegistryDataFrame(registry, vis_config.config)

    tof = TypesOfFormCompleted(types_forms_completed_df, date_start, date_end)

    app = DjangoDash("App", external_stylesheets=[dbc.themes.BOOTSTRAP])

    app.layout = html.Div(
        [
            html.H1(f"Patient Reported Outcomes {registry.name}"),
            chart("Types of Forms Completed", "tof", tof.pie),
        ]
    )

    t2 = datetime.now()
    secs = (t2 - t1).total_seconds()
    logger.debug(f"overall app generated in {secs} seconds")

    return app, secs


def create_graphic(vis_config, data):
    if vis_config.code == "pcf":
        return PatientsWhoCompletedForms(vis_config.config, data).graphic
    elif vis_config.code == "tofc":
        return TypesOfFormCompleted(vis_config.config, data).graphic
    elif vis_config.code == "fgc":
        return FieldGroupComparison(vis_config.config, data).graphic
    else:
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
