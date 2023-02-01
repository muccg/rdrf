import logging
from dash import html, dcc
from ..components.common import BaseGraphic
import dash_bootstrap_components as dbc
from dash import dash_table
import plotly.graph_objects as go
import pandas as pd

logger = logging.getLogger(__name__)


base_colour_map = {
    "1": "green",
    "2": "yellow",
    "3": "orange",
    "4": "red",
    "": "lightgrey",
    None: "lightgrey",
    pd.NA: "white",
}


def get_colour(value):
    return base_colour_map.get(value, "white")


class TrafficLights(BaseGraphic):
    def get_graphic(self):
        data = self._get_table_data()
        return self.get_table(data)

    def get_table(self, table_data):
        seq_names = [html.Th(x) for x in table_data["SEQ_NAME"]]
        table_header = [html.Thead(html.Tr([html.Th("Scale Group"), *seq_names]))]

        groups_config = self.config["groups"]
        groups_dict = {g["name"]: g["fields"] for g in groups_config}

        table_rows = []

        for group_name, fields in groups_dict.items():

            for field in fields:
                field_colour = field + "_colour"
                field_colours = table_data[field_colour]
                table_row = html.Tr(
                    [html.Td(field), *[html.Td(x) for x in field_colours]]
                )
                table_rows.append(table_row)

        table_body = [html.Tbody(table_rows)]
        table = dbc.Table(table_header + table_body)

        return table

    def _get_table_data(self) -> pd.DataFrame:
        groups = self.config["groups"]
        prefix = ["PID", "SEQ", "SEQ_NAME", "TYPE"]
        cdes = []
        for group in groups:
            cdes.extend(group["fields"])

        df = self.data[prefix + cdes]

        logger.debug(f"dataframe columns: {df.columns}")

        for cde in cdes:
            df = self._add_colour_column(cde, df)

        return df

    def _add_colour_column(self, cde, df):
        # https://pandas.pydata.org/docs/reference/api/pandas.Series.map.html
        column_name = cde + "_colour"
        df[column_name] = df[cde].map(get_colour)
        return df
