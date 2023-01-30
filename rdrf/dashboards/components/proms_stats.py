from dashboards.components.common import BaseGraphic
from dash import html
import logging
from datetime import datetime, timedelta
from ..components.tofc import TypesOfFormCompleted

logger = logging.getLogger(__name__)


def log(msg):
    logger.info(f"patient_stats: {msg}")


cdf = "COLLECTIONDATE"


class PatientsWhoCompletedForms(BaseGraphic):
    def get_graphic(self):
        style = {"border": "1px solid"}

        headers = [
            "Time Period",
            "Number of Patients Completing Forms",
            "PROMS Completed",
        ]
        rows = [html.Tr([html.Th(h, style=style) for h in headers])]
        default_periods = ["all", 7, 30, 365]

        time_periods = self.config.get("time_periods", default_periods)

        for time_period in time_periods:
            start_date, end_date = self._get_start_end(time_period)
            n = self._get_num_patients(time_period)
            if time_period == "all":
                desc = f"All time"
            else:
                desc = f"Last {time_period} days"

            rows.append(
                html.Tr(
                    [
                        html.Td(desc, style=style),
                        html.Td(str(n), style=style),
                        html.Td(self._get_pie_chart(time_period), style=style),
                    ],
                    style={"border": "1px solid"},
                )
            )

        table = html.Table(rows, style={"border": "1px solid", "width": "100%"})

        return html.Div([table], "pcf-content")

    def _get_start_end(self, time_period):
        if time_period == "all":
            start_date = self.data[cdf].min()
            end_date = datetime.now()
        elif isinstance(time_period, int):
            delta = timedelta(days=time_period)
            end_date = datetime.now()
            start_date = end_date - delta
        else:
            raise Exception(f"unknown time_period: {time_period}")

        return start_date, end_date

    def _get_pie_chart(self, time_period):
        start_date, end_date = self._get_start_end(time_period)
        df = self.data
        filtered_df = df[(df[cdf] >= start_date) & (df[cdf] <= end_date)]

        tof_graphic = TypesOfFormCompleted("", None, filtered_df).graphic

        return tof_graphic

    def _get_num_patients(self, time_period) -> int:
        log(f"getting number of patients for timeperiod {time_period}")
        df = self.data
        cdf = "COLLECTIONDATE"
        pid = "PID"
        log(f"collection dates = {self.data[cdf]}")

        start_date, end_date = self._get_start_end(time_period)

        log(f"start_date = {start_date}")
        log(f"end_date = {end_date}")

        n = len(df[(df[cdf] >= start_date) & (df[cdf] <= end_date)][pid].unique())
        log(f"n = {n}")
        return n
