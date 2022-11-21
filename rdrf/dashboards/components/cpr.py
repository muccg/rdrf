from .common import BaseGraphic
from dash import dcc, html
from ..data import lookup_cde_value
from ..data import get_cde_values
from ..data import get_percentages_within_seq
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
        pof["per"] = 100 * pof[field] / pof.groupby(SEQ)[field].transform("sum")

        logger.debug(f"pof:\n{pof}")

        logger.debug(f"renaming column per to {label} and resetting index")
        pof = pof.rename(columns={"per": label, field: "counts"}).reset_index()
        logger.debug(f"{pof}")

        logger.debug(f"pof columns = {pof.columns}")
        logger.debug(f"pof index = {pof.index}")
        return pof

    def _create_stacked_bar_px(self, df, field, label):
        logger.debug(f"creating stacked bar for {field} {label}:")
        logger.debug(f"columns = {df.columns}")
        fig = px.bar(
            df,
            SEQ,
            label,
            color=field,
            barmode="stack",
        )

        logger.debug("created bar")
        id = f"bar-{label}"
        div = html.Div([dcc.Graph(figure=fig)], id=id)
        return div
