from django_plotly_dash import DjangoDash
import dash_bootstrap_components as dbc
from rdrf.models.definition.models import Registry
from dashboards.models import VisualisationConfig
from dash import Input, Output, dcc, html

from .utils import get_all_patients_graphics_map
from .utils import get_single_patient_graphics_map
from django.db.utils import ProgrammingError


import logging

logger = logging.getLogger(__name__)

load = True

# this fails during a fresh build because schema not created?
single_app = DjangoDash(
    "SinglePatientDashboardApp", external_stylesheets=[dbc.themes.BOOTSTRAP]
)

all_app = DjangoDash(
    "AllPatientsDashboardApp", external_stylesheets=[dbc.themes.BOOTSTRAP]
)


try:
    registry = Registry.objects.get()
except Registry.DoesNotExist:
    load = False
except Registry.MultipleObjectsReturned:
    load = False
except ProgrammingError:
    # this occurs in the migration check ?
    load = False

if load:
    single_configs = VisualisationConfig.objects.filter(
        registry=registry, dashboard="S"
    ).order_by("position")

    if len(single_configs) == 0:
        tab = ""
    else:
        tab = f"tab_{single_configs[0].id}"

    single_app.layout = dbc.Container(
        [
            dcc.Store(id="store"),
            dbc.Tabs(
                [
                    dbc.Tab(label=f"{vc.title}", tab_id=f"tab_{vc.id}")
                    for vc in single_configs
                ],
                id="tabs",
                active_tab=f"{tab}",
            ),
            html.Div(id="tab-content", className="p-4"),
        ]
    )

    @single_app.expanded_callback(
        Output("tab-content", "children"),
        [Input("tabs", "active_tab")],
    )
    def render_tab_content(*args, **kwargs):

        active_tab = args[0]

        session_state = kwargs["session_state"]
        try:
            patient_id = session_state["patient_id"]
        except KeyError:
            # if session times out we get this
            from django.urls import reverse
            from django.shortcuts import redirect

            login_url = "%s?next=%s" % (
                reverse("two_factor:login"),
                reverse("login_router"),
            )
            return redirect(login_url)

        graphics_map = get_single_patient_graphics_map(
            registry, single_configs, patient_id
        )

        if not active_tab:
            return "No tab selected"
        else:
            return graphics_map[active_tab]

    all_configs = VisualisationConfig.objects.filter(
        registry=registry, dashboard="A"
    ).order_by("position")

    if len(all_configs) == 0:
        tab = ""
    else:
        tab = f"tab_{all_configs[0].id}"

    all_app.layout = dbc.Container(
        [
            dcc.Store(id="session", storage_type="session"),
            dbc.Tabs(
                [
                    dbc.Tab(label=f"{vc.title}", tab_id=f"tab_{vc.id}")
                    for vc in all_configs
                ],
                id="tabs",
                active_tab=f"{tab}",
            ),
            html.Div(id="tab-content", className="p-4"),
        ]
    )

    @all_app.callback(Output("tab-content", "children"), Input("tabs", "active_tab"))
    def render_all_app_tab_content(*args, **kwargs):
        logger.info("dash app all_app callback")
        active_tab = args[0]
        all_patients_graphics_map = get_all_patients_graphics_map(registry, all_configs)

        if not active_tab:
            return "No tab selected"
        else:
            return all_patients_graphics_map[active_tab]

    logger.info("all_app defined")
