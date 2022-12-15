from .common import BaseGraphic
from dash import dcc, html
from ..data import lookup_cde_value
from ..utils import get_colour_map
import plotly.express as px
import pandas as pd

import logging

logger = logging.getLogger(__name__)


def log(msg):
    logger.info(f"cpr: {msg}")


SEQ = "SEQ"  # seq column name


class ChangesInPatientResponses(BaseGraphic):
    """
    A particular list of cdes

    for a given seq number
    calculate the percentages

    for Fatigue
    e.g. 11% Not at all ( green , ie good)
         22% A little   ( dark greeb)
         ..
         33% Very much ( red , ie bad)

    Uses colour map defined in utils

    """

    def set_fields_of_interest(self, config):
        # each fol is a dict {"code": <cde_code>,"label": <text>}
        self.fols = config["fields"]

    def get_graphic(self):
        log("creating Changes in Patient Responses")
        self.set_fields_of_interest(self.config)
        log(f"fields of interest = {self.fols}")
        items = []
        for fol_dict in self.fols:
            field = fol_dict["code"]
            label = fol_dict["label"]
            colour_map = fol_dict.get("colour_map", None)
            pof = self._get_percentages_over_followups(field, label)
            bar_div = self._create_stacked_bar_px(pof, field, label, colour_map)
            items.append(bar_div)

        cpr_div = html.Div([html.H3("Changes in Patient Responses"), *items])
        log("created cpr graphic")

        return html.Div(cpr_div, id="cpr")

    def _get_percentages_over_followups(self, field, label) -> pd.DataFrame:
        pof = self.data.groupby([SEQ, field]).agg({field: "count"})
        pof["Percentage"] = 100 * pof[field] / pof.groupby(SEQ)[field].transform("sum")
        pof = pof.rename(columns={field: "counts"}).reset_index()
        pof[label] = pof[field].apply(lambda value: lookup_cde_value(field, value))

        return pof

    def _create_stacked_bar_px(self, df, field, label, colour_map):
        if colour_map is None:
            colour_map = get_colour_map()

        fig = px.bar(
            df,
            SEQ,
            "Percentage",
            color=label,
            barmode="stack",
            title=f"Change in {label} over time for all patients",
            color_discrete_map=colour_map,
        )

        # self.fix_xaxis(fig, df)

        log("created bar")
        id = f"bar-{label}"
        div = html.Div([dcc.Graph(figure=fig)], id=id)
        return div
