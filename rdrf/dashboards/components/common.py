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
    def __init__(self, title, config_model, data: pd.DataFrame, patient=None):
        self.config_model = config_model
        logger.debug(f"{title} config model = {config_model}")
        self.config = config_model.config
        logger.debug(f"config json = {self.config}")
        self.data = data
        self.title = title
        self.patient = patient  # none if all patients

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
