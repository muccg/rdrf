import plotly.express as px
from .common import BaseGraphic

title = "Types of Form Completed"


class TypesOfFormCompleted(BaseGraphic):
    def bar(self):
        return px.bar(
            self.data,
            x="form",
            y="count",
            title=title,
            width=400,
            height=400,
        )

    def pie(self):
        return px.pie(
            self.data,
            values="count",
            names="form",
            title=title,
            width=400,
            height=400,
        )

    def get_graphic(self):
        return self.pie()
