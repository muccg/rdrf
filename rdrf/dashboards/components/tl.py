import logging
import textwrap
from dash import html
from ..components.common import BaseGraphic
import dash_bootstrap_components as dbc
import pandas as pd
from rdrf.helpers.utils import get_display_value

from rdrf.models.definition.models import CommonDataElement

logger = logging.getLogger(__name__)


# {'code': 'EORTCQLQC30', 'values': [
# {'code': '0', 'value': 'Not at all', 'questionnaire_value': '', 'desc': 'Not at all', 'position': 1}]}
# {'code': '1', 'value': 'A little', 'questionnaire_value': '', 'desc': 'A little', 'position': 2},
# {'code': '2', 'value': 'Quite a bit', 'questionnaire_value': '', 'desc': 'Quite a bit', 'position': 3},
# {'code': '3', 'value': 'Very much', 'questionnaire_value': '', 'desc': 'Very much', 'position': 4},


missing = "grey"

base_colour_map = {
    "0": "green",
    "1": "yellow",
    "2": "orange",
    "3": "red",
    "": missing,
    pd.NA: missing,
    None: missing,
}


display_map = {
    "missing": "lightgrey",
    "not at all": "green",
    "a little": "yellow",
    "quite a bit": "orange",
    "very much": "red",
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


def circle(colour, id):
    return html.Img(src=image_src(f"{colour}-circle"), id=id)


def get_image(base, value, image_id):
    if base == 1:
        if value:
            new_value = str(int(value) - 1)
            value = new_value
    colour = base_colour_map.get(value, "blue")
    if colour == "red":
        return circle("red", image_id)
    elif colour == "orange":
        return circle("orange", image_id)
    elif colour == "yellow":
        return circle("yellow", image_id)
    elif colour == "grey":
        return circle("grey", image_id)
    elif colour == "green":
        return circle("green", image_id)
    else:
        return circle("grey", image_id)


def get_base(field):
    from rdrf.models.definition.models import CommonDataElement

    cde = CommonDataElement.objects.get(code=field)
    try:
        members = [int(s) for s in cde.get_range_members(get_code=True)]
        min_value = min(members)
        return min_value
    except ValueError:
        logger.error(f"tl get_base for {field} is None as codes aren't ints")
        return None


def get_display(field, value):
    d = get_display_value(field, value)
    if not d:
        return "Missing"
    else:
        return d


def get_yes_no(_, value, image_id):
    if value == "1":
        return "Yes"
    elif value == "0":
        return "No"
    else:
        return circle("grey", image_id)


def munge(s, width=30):
    if len(s) > width:
        return html.P(s, className="text-wrap", style={"width": "150px"})
    else:
        return s


def string_field(_, value, image_id):
    if not value:
        return circle("grey", image_id)
    else:
        return munge(value)


def get_popup_info(field, display):
    return f"{field}: {display}"


def get_fields(config):
    return config["fields"]


def get_field_label(cde_code, prop=None):
    from rdrf.models.definition.models import CommonDataElement

    try:
        cde_model = CommonDataElement.objects.get(code=cde_code)
        if prop:
            return getattr(cde_model, prop)
        return cde_model.name
    except CommonDataElement.DoesNotExist:
        return cde_code


def get_popover_target(target_id, body):
    return dbc.Popover(
        dbc.PopoverBody(body),
        target=target_id,
        trigger="hover",
    )


class TrafficLights(BaseGraphic):
    def get_graphic(self):
        self.fields = get_fields(self.config)
        data = self._get_table_data()
        table = self.get_table(data)
        blurb = self._get_blurb()

        return html.Div([blurb, html.Br(), table])

    def _get_blurb(self):
        legend_map = {
            "Not at all": circle("green", "legend-green"),
            "A little": circle("yellow", "legend-yellow"),
            "Quite a bit": circle("orange", "legend-orange"),
            "Very much": circle("red", "legend-red"),
            "Missing": circle("grey", "legend-grey"),
        }

        children = ["Legend: "]

        for value, image in legend_map.items():
            children.append(image)
            children.append(" " + value + " ")

        legend = html.Div(children)

        return html.Div([legend])

    def _get_graphic_function(self, field):
        yes_no = set(["Yes", "No"])
        cde_model = CommonDataElement.objects.get(code=field)
        if cde_model.datatype == "string":
            return string_field
        func = get_image
        if cde_model.pv_group:
            display_values = set(cde_model.get_range_members(get_code=False))
            if display_values == yes_no:
                func = get_yes_no

        return func

    def get_table(self, table_data):
        seq_names = [html.Th(x) for x in table_data["SEQ_NAME"]]
        table_header = [html.Thead(html.Tr([html.Th("Field"), *seq_names]))]
        table_rows = []

        for field in self.fields:
            logger.debug(f"tl field {field}")
            datatype = get_field_label(field, "datatype")
            base = None
            if datatype == "range":
                base = get_base(field)
            field_values = table_data[field]
            image_id = f"image_{field}_"

            graphic_function = self._get_graphic_function(field)

            table_row = html.Tr(
                [
                    html.Td(html.Small(get_field_label(field))),
                    *[
                        html.Td(
                            [
                                graphic_function(
                                    base, value, image_id + "_" + str(index)
                                ),
                                get_popover_target(
                                    image_id + "_" + str(index),
                                    get_popup_info(field, get_display(field, value)),
                                ),
                            ],
                        )
                        for index, value in enumerate(field_values)
                    ],
                ]
            )
            table_rows.append(table_row)

        table_body = [html.Tbody(table_rows)]
        table = dbc.Table(
            table_header + table_body,
            className="table-striped table-sm",
        )

        return table

    def _get_table_data(self) -> pd.DataFrame:
        prefix = ["PID", "SEQ", "SEQ_NAME", "TYPE"]
        cdes = self.fields
        df = self.data[prefix + cdes]

        for cde in cdes:
            df = self._add_colour_column(cde, df)

        for field in cdes:
            display_field = field + "_display"
            df[display_field] = df[field].map(lambda v: get_display_value(field, v))

        return df

    def _add_colour_column(self, cde, df):
        # https://pandas.pydata.org/docs/reference/api/pandas.Series.map.html
        column_name = cde + "_colour"
        df[column_name] = df[cde].map(get_colour)
        return df
