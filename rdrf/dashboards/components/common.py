from dash import dcc, html
import dash_bootstrap_components as dbc


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
