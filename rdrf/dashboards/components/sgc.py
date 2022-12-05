import logging
import pandas as pd
import plotly.express as px
from dash import dcc, html
from rdrf.models.definition.models import CommonDataElement
from ..components.common import BaseGraphic
from ..utils import get_colour_map
from ..utils import get_range

logger = logging.getLogger(__name__)


def log(msg):
    logger.debug(f"sgc: {msg}")


SEQ = "SEQ"


class ScaleGroupError(Exception):
    pass


class ScaleGroupComparison(BaseGraphic):
    def get_graphic(self):
        log("creating Scale Group Comparison")
        fields = [field["code"] for field in self.config["fields"]]
        self.scale = self.get_scale()
        range_value = self.get_range_value(fields)
        log(f"range = {range_value}")
        score_function = self.get_score_function(range_value)

        data = self.calculate_scores(fields, score_function, self.data)

        data = self.calculate_average_scores_over_time(data)

        chart_title = f"{self.scale} score  over time for {self.patient}"

        line_chart = self.get_line_chart(data, chart_title)

        div = html.Div([html.H3(self.title), line_chart])
        return html.Div(div, id=f"sgc-{self.scale}-{self.patient.id}")

    def get_line_chart(self, data, title):
        fig = px.line(data, x=SEQ, y="score", title=title, markers=True)
        fig.update_xaxes(type="category")

        id = f"line-chart-{self.scale}-{self.patient.id}"
        div = html.Div([dcc.Graph(figure=fig)], id=id)
        return div

    def calculate_average_scores_over_time(self, data):
        df = data.groupby(SEQ).agg({"score": "mean"}).reset_index()
        log(f"average scores for {self.scale} over time = ")
        log(f"{df}")
        return df

    def get_scale(self):
        return self.config.get("scale", None)

    def calculate_scores(self, fields, score_function, data):
        def filled(value):
            return value not in [None, ""]

        def rs(row):
            values = [float(row[field]) for field in fields if filled(row[field])]
            n = len(values)
            if n == 0:
                return None
            else:
                avg = sum(values) / len(values)

            return avg

        data["score"] = data.apply(lambda row: score_function(rs(row)), axis=1)
        log(f"data = {data}")
        return data

    def get_score_function(self, range_value):
        scale = self.config["scale"]
        if scale == "functional":
            log("scale is functional")

            def score(rs):
                # rs: raw score = average of values
                if rs is None:
                    return None
                return (1.0 - (rs - 1.0) / range_value) * 100.0

            return score

        elif scale == "symptom":
            log("scale is symptom")

            def score(rs):
                if rs is None:
                    return None
                return ((rs - 1.0) / range_value) * 100.0

            return score

        elif scale == "hs/qol":
            log("scale is hs/qol")

            def score(rs):
                if rs is None:
                    return None
                return ((rs - 1.0) / range_value) * 100.0

            return score
        else:
            log(f"scale is unknown: {scale}")
            raise ScaleGroupError(f"Unknown scale: {scale}")

    def get_range_value(self, fields):
        ranges = set([])
        for field in fields:
            print(f"checking field {field}")
            try:
                cde_model = CommonDataElement.objects.get(code=field)
            except CommonDataElement.DoesNotExist:
                raise ScaleGroupError(f"{field} is nota CDE")
            range_value = get_range(cde_model)
            if range_value is None:
                # not an integer range
                raise ScaleGroupError(f"field {field} not an integer range")
            else:
                ranges.add(range_value)

        if not len(ranges) == 1:
            raise ScaleGroupError(
                f"fields {fields} do not all have the same range: range = {ranges}"
            )
        else:
            ranges = list(ranges)
            range_value = float(ranges[0])

        return range_value
