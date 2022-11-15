import plotly.express as px
from dash import dcc, html
from .common import BaseGraphic
from .common import card

title = "Types of Form Completed"


class TypesOfFormCompleted(BaseGraphic):
    def bar(self):
        return px.bar(
            self.data,
            x="FORM",
            y="count",
            title=title,
            width=400,
            height=400,
        )

    def pie(self):
        return px.pie(
            self.form_counts,
            values="COUNT",
            names="FORM",
            title=title,
            width=400,
            height=400,
        )

    def get_id(self):
        return "tofc"

    def get_graphic(self):
        self.form_counts = (
            self.data["FORM"]
            .value_counts()
            .rename_axis("FORM")
            .reset_index(name="COUNT")
        )

        fig = self.pie()
        div = html.Div([dcc.Graph(figure=fig)], id=self.id)
        return div
