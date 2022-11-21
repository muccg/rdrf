from .common import BaseGraphic
from dash import dcc, html
from ..data import lookup_cde_value
from ..data import get_cde_values
from ..data import get_percentages_within_seq
import plotly.express as px
import plotly.graph_objects as go

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
        seq_nums = list(set(self.data[SEQ]))

        items = []
        for fol in self.fols:
            data = get_percentages_within_seq(self.data, fol)
            bar = px.bar(x=seq_nums, y=data["per"])
            items.append(bar)

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

        # fig = px.bar(
        #    p, x="Percentage", barmode="stack", orientation="h", width=800, height=200
        # )
        fig = self._create_fig_go(p, fol, seq_name, seq)
        # fig = self._create_stacked_bar(p, fol, seq_name, seq)

        div = html.Div([dcc.Graph(figure=fig)], id=id)
        return div

    def _create_fig_go(self, percentages_data, fol, seq_name, seq):

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
            title=title, barmode="stack", showlegend=False, template="presentation"
        )

        return fig

    # def _create_stacked_bar(self, percentages_data, fol, seq_name, seq):
    #     cde_code = fol["code"]
    #     label = fol["label"]
    #     values = percentages_data[label]
    #     percentages = percentages_data["Percentage"]
    #     d = percentages_data
    #     colour_map = {}
    #     colour_map["Very much"] = "red"
    #     colour_map["Quite a bit"] = "orange"
    #     colour_map["A little"] = "pink"
    #     colour_map["Not at all"] = "green"

    #     title = seq_name + " " + label
    #     bar = go.Bar(
    #             x=values,
    #             y=percentages
    #             marker={"color": colour_map["value"]},
    #         )

    #     fig = go.Figure(bar, title=title)

    #     follow_ups=[pair[1] for pair in seqs(self.data)]
    #     follow_up_names = [pair[0] for pair in seqs(self.data)]

    #     fig = go.Figure(data=[
    #         go.Bar(name=value, x=animals, y=[12, 18, 29])
    #                for value in values]
    #     ])
    #     # Change the bar mode
    #     fig.update_layout(barmode='stack')
    #     fig.show()

    #     return fig
