from dash import dcc, html
import dash_bootstrap_components as dbc
import pandas as pd

import logging

logger = logging.getLogger(__name__)


def chart(title, id, figure):
    return html.Div([html.H2(title), dcc.Graph(figure=figure)], id=id)


def card(title, data):
    return dbc.Card(
        dbc.CardBody(
            [
                html.H4(title, className="card-title"),
                html.P(
                    data,
                    className="card-text",
                ),
            ]
        ),
        style={"width": "18rem"},
    )


class BaseGraphic:
    def __init__(
        self,
        title,
        config_model,
        data: pd.DataFrame,
        patient=None,
        all_patients_data=None,
    ):
        self.config_model = config_model
        if self.config_model is not None:
            self.config = config_model.config
        else:
            self.config = None
        self.data = data
        self.title = title
        self.patient = patient  # none if all patients
        self.all_patients_data = all_patients_data  # this gets provided for some single patient components which need to compare

    @property
    def needs_global_data(self):
        return False

    @property
    def graphic(self):
        return self.get_graphic()

    def get_graphic(self):
        raise Exception("subclass responsibility")

    @property
    def id(self):
        return self.get_id()

    def get_id(self):
        raise Exception("subclass responsibility")

    def fix_xaxis(self, fig, data):
        # this replaces the SEQ numbers on the x-axis
        # with names
        fig.update_xaxes(type="category")

        fig.update_layout(
            xaxis=dict(
                tickmode="array", tickvals=data["SEQ"], ticktext=data["SEQ_NAME"]
            )
        )

    def fix_yaxis(self, fig, low=0, high=100):
        fig.update_yaxes(range=[low, high])

    def better_indicator_image(self, good="up"):
        from django.conf import settings

        if settings.SITE_NAME:
            # e.g. cicclinical etc
            base_path = f"/{settings.SITE_NAME}/static"
        else:
            base_path = "/static"

        if good == "up":
            image_src = f"{base_path}/images/dashboards/better_up.png"
        elif good == "down":
            image_src = f"{base_path}/images/dashboards/better_down.png"
        else:
            raise Exception(f"add_indicator should be good=up or good=down not: {good}")

        return image_src

    def add_image(
        self,
        fig,
        image_src,
        x,
        y,
        sizex,
        sizey,
        opacity=0.5,
        layer="below",
        sizing="stretch",
    ):
        fig.add_layout_image(
            dict(
                source=f"{image_src}",
                xref="x",
                yref="y",
                x=x,
                y=y,
                sizex=sizex,
                sizey=sizey,
                sizing=sizing,
                opacity=opacity,
                layer=layer,
            )
        )
