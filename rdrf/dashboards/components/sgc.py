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
        self.mode = "single" if self.patient else "all"
        data = self.data
        scores_map = {}

        for index, group in enumerate(self.config["groups"]):
            group_title = group["title"]
            group_fields = group["fields"]
            if len(group_fields) == 0:
                continue
            group_range = self.get_range_value(group_fields)
            group_scale = group["scale"]
            group_score_function = self.get_score_function(group_range, group_scale)
            score_name = f"score_{index}"
            data = self.calculate_scores(
                score_name, group_fields, group_score_function, data
            )
            if self.mode == "all":
                data = self.calculate_average_scores_over_time(data)

            scores_map[score_name] = group_title  # track so we can plot/annotate

        if self.patient:
            chart_title = f"Scale Group score  over time for {self.patient}"
        else:
            chart_title = f"Scale group score over time for all patients"

        line_chart = self.get_line_chart(data, chart_title, scores_map)

        div = html.Div([html.H3(self.title), line_chart])
        if self.patient:
            id = f"sgc-{self.patient.id}"
        else:
            id = "sgc"

        return html.Div(div, id=id)

    def get_line_chart(self, data, title, scores_map):

        scores_columns = list(scores_map.keys())

        # using multiple lines should be possible now

        fig = px.line(data, x=SEQ, y=scores_columns, title=title, markers=True)

        self.fix_xaxis(fig, data)

        if self.patient:
            id = f"sgc-line-chart-{title}-{self.patient.id}"
        else:
            id = f"sgc-line-chart-{title}-all"

        div = html.Div([dcc.Graph(figure=fig)], id=id)
        return div

    def calculate_average_scores_over_time(self, data):
        # this only makes sense if this chart is passed
        # all patients scores
        df = data.groupby(SEQ).agg({"score": "mean"}).reset_index()
        return df

    def get_scale(self):
        return self.config.get("scale", None)

    def calculate_scores(self, score_name, fields, score_function, data):
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

        data[score_name] = data.apply(lambda row: score_function(rs(row)), axis=1)
        return data

    def get_score_function(self, range_value, scale):
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
                raise ScaleGroupError(f"{field} is not CDE")
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
