from dash import dcc, html
import dash_bootstrap_components as dbc
import pandas as pd


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
    def __init__(self, config, data: pd.DataFrame):
        self.config = config
        self.data = data

    @property
    def graphic(self):
        return self.get_graphic()

    def get_graphic(self):
        raise Exception("subclass responsibility")
