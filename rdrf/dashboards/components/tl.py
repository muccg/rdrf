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
    "3": "amber",
    "4": "red",
    "": "lightgrey",
    None: "lightgrey",
    pd.NA: "white",
}


def get_colour(value):
    return base_colour_map.get(value, "white")


def image_src(name):
    from django.conf import settings

    if settings.SITE_NAME:
        # e.g. cicclinical etc
        base_path = f"/{settings.SITE_NAME}/static"
    else:
        base_path = "/static"

    src = f"{base_path}/images/dashboards/{name}.png"
    return src


def circle(colour):
    return html.Img(src=image_src(f"{colour}-circle"))


def get_image(value):
    try:
        value = int(value)
    except ValueError:
        value = -1

    if value in [6, 7]:
        return circle("green")
    elif value in [1, 2]:
        return circle("red")
    elif value in [3, 4, 5]:
        return circle("blue")
    else:
        return circle("grey")


def get_fields():
    from dashboards.models import VisualisationBaseDataConfig

    c = VisualisationBaseDataConfig.objects.get()
    return [code for code in c.config["fields"] if code.startswith("EORTCQLQC30")]


def get_field_label(cde_code):
    from rdrf.models.definition.models import CommonDataElement

    try:
        cde_model = CommonDataElement.objects.get(code=cde_code)
        return cde_model.name
    except CommonDataElement.DoesNotExist:
        return cde_code


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
            fields2 = get_fields()

            for field in fields2:
                field_values = table_data[field]
                table_row = html.Tr(
                    [
                        html.Td(get_field_label(field)),
                        *[html.Td(get_image(value)) for value in field_values],
                    ]
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

        fields = get_fields()

        df = self.data[prefix + fields]

        logger.debug(f"dataframe columns: {df.columns}")

        for cde in cdes:
            df = self._add_colour_column(cde, df)

        return df

    def _add_colour_column(self, cde, df):
        # https://pandas.pydata.org/docs/reference/api/pandas.Series.map.html
        column_name = cde + "_colour"
        df[column_name] = df[cde].map(get_colour)
        return df
