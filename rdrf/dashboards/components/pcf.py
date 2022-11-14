import plotly.express as px
from ..common import card, BaseGraphic


class PatientsWhoCompletedForms(BaseGraphic):

    def get_graphic(self):
        start_date = self.data["COLLECTIONDATE"].min()
        end_date = self.data["COLLECTIONDATE"].max()
        num_patients = self._get_number_patients(self.start_date, self.end_date)
        
        return card("Patients Who Have Completed Forms", str(num_patients)

    def _get_number_patients(self, start_date, end_date):
        df = self.data
        cdf = "COLLECTIONDATE"
        return len(df[(df[cdf] >= start_date) & (df[cdf] <= end_date)][pid].unique())

