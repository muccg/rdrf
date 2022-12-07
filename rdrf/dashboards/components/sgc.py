import logging
import pandas as pd
import plotly.express as px
from dash import dcc, html
from rdrf.models.definition.models import CommonDataElement
from ..components.common import BaseGraphic
from ..utils import get_colour_map
from ..utils import get_range, get_base

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
            scores_map[score_name] = group_title  # track so we can plot/annotate

        if self.mode == "all":
            data = self.calculate_average_scores_over_time(data, score_names)
            chart_title = f"Scale group score over time for all patients"
            id = "sgc"
        else:
            chart_title = f"Scale group scores over time for {self.patient.link}"
            id = f"sgc-{self.patient.id}"

        line_chart = self.get_line_chart(data, chart_title, scores_map)

        div = html.Div([html.H3(self.title), line_chart])

        return html.Div(div, id=id)

    def get_line_chart(self, data, title, scores_map):
        score_names = sorted(list(scores_map.keys()))
        fig = px.line(
            data,
            x=SEQ,
            y=score_names,
            title=title,
            markers=True,
            labels={"SEQ": "Time"},
        )

        self.fix_xaxis(fig, data)

        scores_map["seq"] = "Time"
        fig.for_each_trace(
            lambda t: t.update(
                name=scores_map[t.name],
                legendgroup=scores_map[t.name],
                hovertemplate=t.hovertemplate.replace(t.name, scores_map[t.name]),
            )
        )

        if self.patient:
            id = f"sgc-line-chart-{title}-{self.patient.id}"
        else:
            id = f"sgc-line-chart-{title}-all"

        div = html.Div([dcc.Graph(figure=fig)], id=id)
        return div

    def calculate_average_scores_over_time(self, data, score_names):
        # this only makes sense if this chart is passed
        # all patients scores
        aggregations_map = {score_name: "mean" for score_names in score_names}

        df = data.groupby(SEQ).agg(aggregations_map).reset_index()
        return df

    def get_scale(self):
        return self.config.get("scale", None)

    def calculate_scores(self, score_name, fields, score_function, data):
        logger.debug(f"calculate scores for {score_name} {fields}")

        detected_bases = set([get_base(field) for field in fields])
        if len(detected_bases) > 1:
            raise Exception(f"different bases for fields {fields}: {detected_bases}")

        detected_base = list(detected_bases)[0]  # 0 or 1

        if detected_base == 0:
            delta = 1.0
        elif detected_base == 1:
            delta = 0.0
        else:
            raise Exception(f"base of fields {fields} is {detected_base}")

        def filled(value):
            return value not in [None, ""]

        def rs(row):
            logger.debug(f"calculating raw score for fields")
            values = [
                float(row[field]) + delta for field in fields if filled(row[field])
            ]
            logger.debug(f"values = {values}")
            n = len(values)
            logger.debug(f"num values = {n}")
            if n == 0:
                return None
            else:
                avg = sum(values) / len(values)

            logger.debug(f"rs(avg) = {avg}")

            return avg

        data[score_name] = data.apply(lambda row: score_function(rs(row)), axis=1)
        return data

    def get_score_function(self, range_value, scale):
        if scale == "functional":
            log("scale is functional")

            def score(rs):
                logger.debug(f"functional score: rs = {rs}")
                logger.debug(
                    f"functional score: range value = {range_value} scale = {scale}"
                )
                # rs: raw score = average of values
                if rs is None:
                    logger.debug(f"scaled score returning None")
                    return None
                s = (1.0 - (rs - 1.0) / range_value) * 100.0
                logger.debug(f"scaled score = {s}")
                return s

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
        bases = set([])
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
