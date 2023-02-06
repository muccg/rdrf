from .common import BaseGraphic
from dash import dcc, html
from ..data import lookup_cde_value
from ..utils import get_colour_map
from ..utils import add_seq_name
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
        self.set_fields_of_interest(self.config)
        items = []
        for fol_dict in self.fols:
            field = fol_dict["code"]
            label = fol_dict["label"]
            colour_map = fol_dict.get("colour_map", None)
            pof = self._get_percentages_over_followups(field, label)
            bar_div = self._create_stacked_bar_px(pof, field, label, colour_map)
            items.append(bar_div)

        blurb_text = """
                This tab displays EORTC QLQ-C30 symptom scale results for all patients
                over the time intervals that PROMs have been completed.
                Scroll down to see all variables.
                """

        blurb = html.P(blurb_text)

        cpr_div = html.Div([html.H3("Changes in Patient Responses"), blurb, *items])

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

        df = add_seq_name(df)
        df = df.round(1)
        df["text"] = df.apply(
            lambda row: "<b>"
            + str(row["counts"])
            + " ("
            + str(row["Percentage"])
            + "%)"
            + "</b>",
            axis=1,
        )

        fig = px.bar(
            df,
            SEQ,
            "Percentage",
            color=label,
            barmode="stack",
            title=f"Change in {label} over time for all patients",
            color_discrete_map=colour_map,
            text="text",
            labels={"SEQ": "Survey Time Period", "text": "Summary"},
        )

        self.fix_xaxis(fig, df)
        self.set_background_colour(fig, "rgb(250, 250, 250)")

        id = f"bar-{label}"
        div = html.Div([dcc.Graph(figure=fig)], id=id)
        return div

    def fix_xaxis(self, fig, data):
        # this replaces the SEQ numbers on the x-axis
        # with names
        fig.update_xaxes(type="category")

        seq_totals = data.groupby(["SEQ"])["counts"].sum()

        def get_ticktext(row):
            seq = row["SEQ"]
            seq_total = seq_totals[seq]
            seq_name = row["SEQ_NAME"]
            return seq_name + " (" + str(seq_total) + ")"

        data["ticktext"] = data.apply(get_ticktext, axis=1)

        fig.update_layout(
            xaxis=dict(
                tickmode="array", tickvals=data["SEQ"], ticktext=data["ticktext"]
            )
        )
