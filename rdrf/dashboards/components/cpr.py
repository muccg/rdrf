from .common import BaseGraphic
from dash import dcc, html
from ..data import lookup_cde_value
from ..data import get_cde_values
from ..data import get_percentages_within_seq
from ..utils import get_colour_map
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

import logging

logger = logging.getLogger(__name__)

SEQ = "SEQ"  # seq column name


def seqs(df):
    i = 0
    max_seq = df["SEQ"].max()
    logger.debug(f"seq max = {max_seq}")
    yield "Baseline", i
    i += 1
    while i <= max_seq:
        yield f"Follow Up {i}", i
        i += 1


class ChangesInPatientResponses(BaseGraphic):
    """
    A particular list of cdes

    for a given seq number
    calculate the percentages

    for Fatigue
    e.g. 11% Not at all ( green , ie good)
         22% A little   ( beige)
         ..
         33% Very much ( red , ie bad)

    """

    def set_fields_of_interest(self, config):
        # each fol is a dict {"code": <cde_code>,"label": <text>}

        self.fols = config["fields_of_interest"]

    def get_graphic(self):
        logger.debug("creating Changes in Patient Responses")
        self.set_fields_of_interest(self.config)
        logger.debug(f"fields of interest = {self.fols}")
        items = []
        for fol_dict in self.fols:
            field = fol_dict["code"]
            label = fol_dict["label"]
            logger.debug(f"field = {field}")
            pof = self._get_percentages_over_followups(field, label)
            bar_div = self._create_stacked_bar_px(pof, field, label)
            items.append(bar_div)

        cpr_div = html.Div([html.H3("Changes in Patient Responses"), *items])
        logger.debug("created cpr graphic")

        return html.Div(cpr_div, id="cpr")

    def _get_percentages_over_followups(self, field, label) -> pd.DataFrame:
        logger.debug(f"get percentages over followups (pof) for {field} {label}")
        pof = self.data.groupby([SEQ, field]).agg({field: "count"})
        pof["Percentage"] = 100 * pof[field] / pof.groupby(SEQ)[field].transform("sum")

        pof = pof.rename(columns={field: "counts"}).reset_index()
        pof[label] = pof[field].apply(lambda value: lookup_cde_value(field, value))

        return pof

    def _create_stacked_bar_px(self, df, field, label):
        colour_map = get_colour_map()
        fig = px.bar(
            df,
            SEQ,
            "Percentage",
            color=label,
            barmode="stack",
            color_discrete_map=colour_map,
        )

        logger.debug("created bar")
        id = f"bar-{label}"
        div = html.Div([dcc.Graph(figure=fig)], id=id)
        return div
