from dashboards.components.common import BaseGraphic
from dash import html
import logging
from datetime import datetime, timedelta
from ..components.tofc import TypesOfFormCompleted
import dash_bootstrap_components as dbc

logger = logging.getLogger(__name__)


def log(msg):
    logger.info(f"patient_stats: {msg}")


cdf = "COLLECTIONDATE"


class PatientsWhoCompletedForms(BaseGraphic):
    def get_graphic(self):

        headers = [
            "Time Period",
            "Number of Patients Completing PROMS",
            "PROMS Completed",
        ]
        table_header = [html.Thead(html.Tr([html.Th(h) for h in headers]))]
        default_periods = ["all", 7, 30, 365]

        time_periods = self.config.get("time_periods", default_periods)
        rows = []

        for time_period in time_periods:
            start_date, end_date = self._get_start_end(time_period)
            n = self._get_num_patients(time_period)
            if time_period == "all":
                desc = "All time"
            else:
                desc = f"Last {time_period} days"

            if time_period == 7:
                links = self._get_links(start_date, end_date)
                logger.debug(f"links = {links}")
            else:
                links = []

            if links:
                links_div = html.Div(links)
            else:
                links_div = None

            desc_td = html.Td(desc)
            logger.debug(f"desc td = {desc_td}")

            rows.append(
                html.Tr(
                    [
                        desc_td,
                        html.Td([str(n), links_div]),
                        html.Td(self._get_pie_chart(time_period)),
                    ]
                )
            )

        table_body = [html.Tbody([*rows])]
        table = dbc.Table(table_header + table_body)

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

    def _get_links(self, start_date, end_date):
        from rdrf.helpers.utils import get_form_url
        from registry.patients.models import Patient

        links = []
        df = self.data
        df = df[(df[cdf] >= start_date) & (df[cdf] <= end_date)]

        for index, row in df.iterrows():
            try:
                pid = row["PID"]
                patient = Patient.objects.get(id=pid)
                context_id = row["CONTEXT_ID"]
                collection_date = row["COLLECTIONDATE"].date()
                form_name = row["FORM"]
                record_type = row["TYPE"]

                url = get_form_url(
                    self.config_model.registry, pid, context_id, form_name
                )
                title = f"{record_type} {patient} ({collection_date})"
                links.append(html.A(html.P(title), href=url))
            except Exception as ex:
                logger.error(f"error building link: {ex}")
        return links
