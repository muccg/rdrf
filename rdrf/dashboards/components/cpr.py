from .common import BaseGraphic
from dash import dcc, html
from ..data import lookup_cde_value
from ..utils import get_colour_map
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

import logging

logger = logging.getLogger(__name__)

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

        self.fols = config["fields_of_interest"]

    def get_graphic(self):
        logger.debug("creating Changes in Patient Responses")
        self.set_fields_of_interest(self.config)
        logger.debug(f"fields of interest = {self.fols}")
        items = []
        for fol_dict in self.fols:
            field = fol_dict["code"]
            label = fol_dict["label"]
            field_type = fol_dict.get("type", "cde")
            logger.debug(f"field = {field}")
            if field_type == "calculation":
                self.data[field] = self.perform_calculation(field)
            pof = self._get_percentages_over_followups(field, label)
            bar_div = self._create_stacked_bar_px(pof, field, label)
            items.append(bar_div)

        cpr_div = html.Div([html.H3("Changes in Patient Responses"), *items])
        logger.debug("created cpr graphic")

        return html.Div(cpr_div, id="cpr")

    def perform_calculation(self, field):
        # base "normal" cpr just works on cde fields so not used
        raise Exception("subclass responsiblity")

    def _get_percentages_over_followups(self, field, label) -> pd.DataFrame:
        pof = self.data.groupby([SEQ, field]).agg({field: "count"})
        pof["Percentage"] = 100 * pof[field] / pof.groupby(SEQ)[field].transform("sum")
        pof = pof.rename(columns={field: "counts"}).reset_index()
        pof[label] = pof[field].apply(lambda value: lookup_cde_value(field, value))

        return pof

    def get_colour_map(self):
        return get_colour_map()

    def _create_stacked_bar_px(self, df, field, label):
        colour_map = self.get_colour_map()
        labels = self._get_labels(df)
        fig = px.bar(
            df,
            SEQ,
            "Percentage",
            color=label,
            barmode="stack",
            title=f"Change in {label} over time for all patients",
            color_discrete_map=colour_map,
        )

        logger.debug("created bar")
        id = f"bar-{label}"
        div = html.Div([dcc.Graph(figure=fig)], id=id)
        return div

    def _get_labels(self, df):
        d = {0: "Baseline"}

        def seq_name(value):
            return d.get(value, f"Follow Up {value}")

        seq_values = [seq_name(value) for value in df[SEQ]]
        logger.debug(f"seq values = {seq_values}")

        return {"SEQ": seq_values}
