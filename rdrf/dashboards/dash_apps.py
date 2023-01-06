from django_plotly_dash import DjangoDash
import dash_bootstrap_components as dbc
from rdrf.models.definition.models import Registry
from dashboards.models import VisualisationConfig
from dash import Input, Output, dcc, html

registry = Registry.objects.get()

all_configs = VisualisationConfig.objects.filter(
    registry=registry, dashboard="A"
).order_by("position")

single_configs = VisualisationConfig.objects.filter(
    registry=registry, dashboard="S"
).order_by("position")


single_app = DjangoDash(
    "SinglePatientDashboardApp", external_stylesheets=[dbc.themes.BOOTSTRAP]
)

single_app.layout = dbc.Container(
    [
        dcc.Store(id="store"),
        dbc.Tabs(
            [
                dbc.Tab(label=f"{vc.title}", tab_id=f"tab_{vc.id}")
                for vc in single_configs
            ],
            id="tabs",
            active_tab=f"tab_{single_configs[0].id}",
        ),
        html.Div(id="tab-content", className="p-4"),
    ]
)


@single_app.callback(
    Output("tab-content", "children"),
    [Input("tabs", "active_tab")],
)
def render_tab_content(active_tab):
    if not active_tab:
        return "No tab selected"
    else:
        return graphics_map[active_tab]


all_app = DjangoDash(
    "AllPatientsDashboardApp", external_stylesheets=[dbc.themes.BOOTSTRAP]
)
