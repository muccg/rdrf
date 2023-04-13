import logging
from dash import html
from ..components.common import BaseGraphic
import dash_bootstrap_components as dbc
import pandas as pd
from rdrf.helpers.utils import get_display_value

from ..utils import assign_seq_names

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
    elif colour == "burgundy":
        return circle("burgundy", image_id)
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


class TrafficLights(BaseGraphic):
    def get_graphic(self):
        self.fields = get_fields(self.config)
        self.colour_map = self._get_colour_map(self.config)
        self.legend_map = self._get_legend_map(self.config)

        data = self._get_table_data()
        table = self.get_table(data)
        blurb = self._get_blurb()

        return html.Div([blurb, html.Br(), table])

    def _get_colour_map(self, config):
        return config.get("colour_map", None)

    def _get_legend_map(self, config):
        m = config.get("legend", None)
        if not m:
            return None

        legend_map = {}
        for english in config["legend_order"]:
            colour = m[english]
            legend_map[english] = circle(colour, f"legend-{colour}")
        return legend_map

    def _get_blurb(self):
        legend_map = {
            "Not at all": circle("green", "legend-green"),
            "A little": circle("yellow", "legend-yellow"),
            "Quite a bit": circle("orange", "legend-orange"),
            "Very much": circle("red", "legend-red"),
            "Missing": circle("grey", "legend-grey"),
        }

        if self.legend_map:
            legend_map = self.legend_map

        children = ["Legend: "]

        for value, image in legend_map.items():
            children.append(image)
            children.append(" " + value + " ")

        legend = html.Div(children)

        missing_baseline = self._is_missing_baseline()
        notes = (
            " Note: Patient is missing a Baseline Form" if missing_baseline else None
        )
        children = [legend, notes] if notes else [legend]

        return html.Div(children)

    def _get_graphic_function(self, field):
        yes_no = set(["Yes", "No"])
        cde_model = CommonDataElement.objects.get(code=field)
        if cde_model.datatype == "string":
            return string_field
        # func = get_image
        func = self.get_image2
        if cde_model.pv_group:
            display_values = set(cde_model.get_range_members(get_code=False))
            if display_values == yes_no:
                func = get_yes_no

        return func

    def get_image2(self, base, value, image_id):
        if self.colour_map:
            colour_map = self.colour_map
        else:
            colour_map = base_colour_map
        if base == 1:
            if value:
                new_value = str(int(value) - 1)
                value = new_value

        colour = colour_map.get(value, None)
        if colour:
            return circle(colour, image_id)
        return circle("grey", image_id)

    def get_table(self, table_data):
        seq_names = [html.Th(x) for x in table_data["SEQ_NAME"]]
        table_header = [html.Thead(html.Tr([html.Th("Field"), *seq_names]))]
        table_rows = []

        for field in self.fields:
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
                                )
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
        prefix = ["PID", "SEQ", "SEQ_NAME", "FORM", "TYPE", "COLLECTIONDATE"]
        cdes = self.fields
        df = self.data[prefix + cdes]

        for cde in cdes:
            df = self._add_colour_column(cde, df)

        for field in cdes:
            display_field = field + "_display"
            df[display_field] = df[field].map(lambda v: get_display_value(field, v))

        # for BC need to ensure the static followups are in the correct order
        if self.static_followups:
            logger.debug(f"there are static followups = {self.static_followups}")
            df = self._fix_ordering_of_static_followups(df)
        else:
            logger.debug("no static followups!")

        return df

    def _fix_ordering_of_static_followups(self, df):
        logger.debug("fixing static followups:")
        static_followups = [
            x["name"] for x in self.static_followups["followups"] if x["seq"] != "+"
        ]
        baseline_form = self.static_followups["baseline"]
        logger.debug(f"static followups = {static_followups}")
        changed = False
        for index, row in df.iterrows():
            if row["FORM"] == baseline_form:
                old_seq = row["SEQ"]
                df.at[index, "SEQ"] = 0
                logger.debug(f"""static baseline fix: {row["FORM"]} {old_seq} -> 0""")
                changed = True
            elif row["FORM"] in static_followups:
                logger.debug(f"""fixing row for static followup {row["FORM"]}""")
                self._fixup_static_followup(df, index, row)
                changed = True

        if changed:
            from rdrf.models.definition.models import RegistryForm

            def static_get_seq_name(seq, form):
                if form == self.static_followups["baseline"]:
                    form_model = RegistryForm.objects.get(name=form)
                    return form_model.display_name
                else:
                    for form_dict in self.static_followups["followups"]:
                        if form_dict["name"] == form:
                            form_model = RegistryForm.objects.get(name=form)
                            return form_model.display_name

            df = assign_seq_names(df, static_get_seq_name).sort_values(by="SEQ")

        return df

    def _fixup_static_followup(self, df, index, row):
        # the metadata looks like
        # self.static_followups is a dict
        # with keys
        # "followup_forms": [{"seq": 1, "name": "FollowUpPROMS6months"},
        # {"seq": 2, "name": "FUpPROMSYr1"},
        # {"seq": 3, "name": "FUpPROMSYr2"},
        # {"seq": "+", "name": "FUpPROMS3_10Years"}]
        # baseline_form : "<baseline> form
        form = row["FORM"]
        for static_form_dict in self.static_followups["followups"]:
            if static_form_dict["name"] == form:
                static_seq = static_form_dict["seq"]
                old_seq = row["SEQ"]
                df.at[index, "SEQ"] = static_seq
                logger.debug(
                    f"""static fu fix: {row["FORM"]} {old_seq} -> {static_seq}"""
                )

    def _add_colour_column(self, cde, df):
        # https://pandas.pydata.org/docs/reference/api/pandas.Series.map.html
        column_name = cde + "_colour"
        df[column_name] = df[cde].map(get_colour)
        return df
