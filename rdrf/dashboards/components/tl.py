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


class ColourMap:
    def __getitem__(self, index):
        return base_colour_map.get(index, "white")

    def __call__(self, index):
        return self[index]


class TrafficLights(BaseGraphic):
    def get_graphic(self):
        data = self._get_table_data()
        return self.get_table(data)

    def get_table(self, table_data):
        # first column is the field
        # field, baseline , fu1 , fu2 , .. fuN
        logger.debug(table_data.columns)

        num_followups = len(table_data.columns) - 2

        headers = ["Scale Group", "Baseline"] + [
            f"Follow {i}" for i in range(1, num_followups + 1)
        ]

        table_header = [html.Thead(html.Tr([html.Th(h) for h in headers]))]

        groups_config = self.config["groups"]

        groups_dict = {g["name"]: g["fields"] for g in groups_config}

        table_rows = []

        for group_name, fields in groups_dict.items():

            for field in fields:
                logger.debug(f"checking {field}")
                table_row = []
                table_row.append(field)
                field_colour = field + "_colour"
                for index, row in table_data.iterrows():
                    colour = row[field_colour]
                    table_row.append(colour)

                table_row = html.Tr([html.Td(x) for x in table_row])

                table_rows.append(table_row)

        table_body = [html.Tbody(table_rows)]
        table = dbc.Table(table_header + table_body)

        return table

    def _get_table_data(self) -> pd.DataFrame:
        cm = ColourMap()
        groups = self.config["groups"]
        prefix = ["PID", "SEQ", "SEQ_NAME", "TYPE"]
        cdes = []
        for group in groups:
            cdes.extend(group["fields"])

        df = self.data[prefix + cdes]

        logger.debug(f"dataframe columns: {df.columns}")

        for cde in cdes:
            df = self._add_colour_column(cde, df, cm)

        return df

    def _add_colour_column(self, cde, df, cm):
        # https://pandas.pydata.org/docs/reference/api/pandas.Series.map.html
        column_name = cde + "_colour"
        df[column_name] = df[cde].map(cm)
        return df
