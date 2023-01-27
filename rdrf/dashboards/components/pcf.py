from dashboards.components.common import BaseGraphic
from dash import html
import logging

logger = logging.getLogger(__name__)


def log(msg):
    logger.info(f"pcf: {msg}")


class PatientsWhoCompletedForms(BaseGraphic):
    def get_graphic(self):

        start_date = self.data["COLLECTIONDATE"].min()
        end_date = self.data["COLLECTIONDATE"].max()

        num_patients = self._get_number_patients(start_date, end_date)

        text = html.P(
            "Number of Patients completing PROMS ( Baseline or FollowUps) over all time:"
        )

        p = html.B(f"{num_patients}")

        return html.Div([text, p], "pcf-content")

    def _get_number_patients(self, start_date, end_date):
        df = self.data
        cdf = "COLLECTIONDATE"
        pid = "PID"
        return len(df[(df[cdf] >= start_date) & (df[cdf] <= end_date)][pid].unique())
