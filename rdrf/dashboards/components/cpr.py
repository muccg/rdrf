from .common import BaseGraphic
from dash import dcc, html
from ..data import lookup_cde_value
from ..data import get_cde_values
import plotly.express as px

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

        items = []
        for fol in self.fols:
            for seq_name, seq in seqs(self.data):
                bar_div = self._create_bar(fol, seq_name, seq)
                items.append(bar_div)

        cpr_div = html.Div([html.H3("Changes in Patient Responses"), *items])

        return html.Div(cpr_div, id="cpr")

    def _create_bar(self, fol, seq_name, seq):
        code = fol["code"]
        label = fol["label"]
        df = self.data
        id = label + "_" + seq_name

        p = (
            df[df[SEQ] == seq][code]
            .value_counts(normalize=True)
            .rename_axis(label)
            .reset_index(name="Percentage")
        )
        p["Percentage"] = p["Percentage"].apply(lambda value: 100.0 * value)
        p[label] = p[label].apply(lambda value: lookup_cde_value(code, value))
        logger.debug(p)

        # fig = px.bar(
        #    p, x="Percentage", barmode="stack", orientation="h", width=800, height=200
        # )
        fig = self._create_fig_go(p, fol, seq_name, seq)

        div = html.Div([dcc.Graph(figure=fig)], id=id)
        return div

    def _create_fig_go(self, percentages_data, fol, seq_name, seq):
        import plotly.graph_objects as go

        cde_code = fol["code"]
        logger.debug(f"code = {cde_code}")
        label = fol["label"]
        values = percentages_data[label]

        logger.debug(f"{label} values = {values}")
        percentages = percentages_data["Percentage"]

        title = seq_name + " " + label

        fig = go.Figure(
            go.Bar(
                x=values,
                y=percentages,
            )
        )

        fig.update_layout(
            title=title, barmode="overlay", showlegend=False, template="presentation"
        )

        return fig
