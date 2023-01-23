import logging
from dash import html, dcc
from ..components.common import BaseGraphic

from dash import dash_table
import plotly.graph_objects as go
import pandas as pd

logger = logging.getLogger(__name__)


def log(msg):
    logger.info(f"tl: {msg}")


colour_map = {"1": "green", "2": "yellow", "3": "orange", "4": "red", "": "lightgrey"}


class TrafficLights(BaseGraphic):
    def get_graphic(self):
        data = self._get_table_data()
        return self.get_table(data)

    def traffic_light_colour(self, value):
        return colour_map.get(value, "lightgrey")

    def get_table(self, table_data):
        # div = html.Div([dcc.Graph(figure=fig)], id="trafficlights")
        return html.Div("traffic lights")

    def _get_table_data(self) -> pd.DataFrame:
        groups = self.config["groups"]
        cdes = []
        for group in groups:
            cdes.extend(group["fields"])

        logger.debug(self.data)
        df = self.data[cdes]
        logger.debug(f"table data:\n{df}")

        return df
