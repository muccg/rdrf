from .common import BaseGraphic
from dash import dcc, html

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

    def _create_elements(self, items):
        return html.H2("Changes in Patient Responses will appear here")

    def get_graphic(self):
        logger.debug("creating Changes in Patient Responses")
        self.set_fields_of_interest(self.config)

        items = []
        for seq_name, seq in seqs(self.data):
            logger.debug(f"calculating {seq_name}...")
            for fol in self.fols:
                logger.debug(f"checking {fol}...")
                bar = self._create_bar(fol, seq_name, seq)
                items.append((field, seq_name, seq, bar))

        logger.debug(f"items = {items}")
        elements = self._create_elements(items)

        return html.Div(elements, id="cpr")

    def _create_bar(self, fol, seq_name, seq):
        code = fol["code"]
        label = fol["label"]
        df = self.data
        percentages = 100.0 * df[df[SEQ] == seq][code].value_counts(normalize=True)
        print(f"percentages = {percentages}")
        percentages_df = percentages.rename_axis("PERCENTAGE").reset_index(label)
        print(f"percentages_df = {percentages_df}")
