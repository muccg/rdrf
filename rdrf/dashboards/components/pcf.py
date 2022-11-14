import plotly.express as px
from dashboards.components.common import card, BaseGraphic
import logging

logger = logging.getLogger(__name__)


def log(msg):
    logger.debug(f"pcf: {msg}")


class PatientsWhoCompletedForms(BaseGraphic):
    def get_graphic(self):
        start_date = self.data["COLLECTIONDATE"].min()
        end_date = self.data["COLLECTIONDATE"].max()
        log(f"start date = {start_date}")
        log(f"end date = {end_date}")

        num_patients = self._get_number_patients(start_date, end_date)
        log(f"num_patients = {num_patients}")

        return card("Patients Who Have Completed Forms", str(num_patients))

    def _get_number_patients(self, start_date, end_date):
        df = self.data
        cdf = "COLLECTIONDATE"
        pid = "PID"
        return len(df[(df[cdf] >= start_date) & (df[cdf] <= end_date)][pid].unique())
