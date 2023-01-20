import logging
from datetime import datetime
import plotly.express as px
import pandas as pd
from dash import dcc, html
from rdrf.models.definition.models import CommonDataElement
from ..components.common import BaseGraphic
from ..utils import get_range, get_base
from ..data import combine_data


logger = logging.getLogger(__name__)


def log(msg):
    logger.info(f"sgc: {msg}")


SEQ = "SEQ"


class ScaleGroupError(Exception):
    pass


class AllPatientsScoreHelper:
    def __init__(self, scg, score_name, title, fields, score_function):
        self.sgc = scg
        self.score_name = score_name
        self.title = title
        self.fields = fields
        self.score_function = score_function

    def calculate_score(self, data):
        data = self.sgc.calculate_scores(
            self.score_name, self.fields, self.score_function, data
        )
        return data


class ScaleGroupComparison(BaseGraphic):
    def get_graphic(self):
        self.better = None
        log("creating Scale Group Comparison")
        self.mode = "single" if self.patient else "all"
        data = self.data
        scores_map = {}
        self.group_info = {}
        self.rev_group = {}
        self.all_patients_helpers = []
        self.average_scores = None
        group_scales = set([])

        for index, group in enumerate(self.config["groups"]):
            group_title = group["title"]
            group_fields = group["fields"]
            if len(group_fields) == 0:
                continue

            group_range = self.get_range_value(group_fields)
            group_scale = group["scale"]
            group_scales.add(group_scale)
            group_score_function = self.get_score_function(group_range, group_scale)
            score_name = f"score_{index}"
            self.group_info[score_name] = group_title
            self.rev_group[group_title] = score_name
            logger.info(f"calculating score for {group_title}")
            data = self.calculate_scores(
                score_name, group_fields, group_score_function, data
            )

            scores_map[score_name] = group_title  # track so we can plot/annotate
            compare_all = group.get("compare_all", False)
            if compare_all:
                helper = AllPatientsScoreHelper(
                    self, score_name, group_title, group_fields, group_score_function
                )
                self.all_patients_helpers.append(helper)

        score_names = list(scores_map.keys())

        if self.all_patients_helpers:
            # if we do need to compare to the average scores
            # with all the patients, we need to append columns
            # to the dataframe showing the average scores
            if self.all_patients_data is None:
                logger.info("all patients data not loaded - loading ..")
                t1 = datetime.now()
                self.load_all_patients_data()
                t2 = datetime.now()
                logger.info(f"time taken = {(t2-t1).total_seconds()} seconds")

            logger.info("calculating scores for all patients..")
            t1 = datetime.now()
            for helper in self.all_patients_helpers:
                self.all_patients_data = helper.calculate_score(self.all_patients_data)

            t2 = datetime.now()
            logger.info(
                f"time taken to calculate all scores for all patients = {(t2-t1).total_seconds()} seconds"
            )

            # now work out the average per SEQ
            logger.info("calculating averages for the scores..")
            t1 = datetime.now()
            all_patients_score_names = [h.score_name for h in self.all_patients_helpers]
            average_scores = self.calculate_average_scores_over_time(
                self.all_patients_data, all_patients_score_names
            )
            t2 = datetime.now()
            logger.info(
                f"time taken to calculate average scores for all patients = {(t2-t1).total_seconds()} seconds"
            )

        else:
            average_scores = None

        if self.mode == "all":
            # not sure if this is actually required
            data = self.calculate_average_scores_over_time(data, score_names)
            chart_title = "Scale group score over time for all patients"
            sgc_id = "sgc"
        else:
            chart_title = f"Scores over time for {self.patient.link}"
            sgc_id = f"sgc-{self.patient.id}"

        if average_scores is not None:
            data = combine_data(data, average_scores)
            score_names = [sn for sn in scores_map if sn.startswith("score_")]
            score_names = score_names + ["avg_" + sn for sn in score_names]
            for sn in score_names:
                if sn.startswith("avg_score"):
                    orig = sn.replace("avg_", "")
                    orig_display_name = scores_map[orig]
                    avg_display_name = "Average " + orig_display_name
                    scores_map[sn] = avg_display_name

        scales = list(group_scales)
        if len(scales) == 1:
            scale = scales[0]
            if scale == "symptom":
                self.better = "down"
            elif scale in ["functional", "hs/qol"]:
                self.better = "up"
            else:
                self.better = None
        else:
            self.better = None

        if self.better == "up":
            chart_title += " <i>( Higher score is better )</i>"
        elif self.better == "down":
            chart_title += " <i>( Lower score is better )</i>"

        line_chart = self.get_line_chart(data, chart_title, scores_map)
        table = self.get_table(data, scores_map)

        div = html.Div([line_chart, table])

        return html.Div(div, id=sgc_id)

    @property
    def needs_global_data(self):
        if "groups" in self.config:
            for scale_group in self.config["groups"]:
                if "compare_all" in scale_group:
                    if scale_group["compare_all"]:
                        return True

    def calculate_all_patients_scores(self, data):
        # data is one single patients data
        if self.all_patients_data is None:
            self.load_all_patients_data()

        avg_data = self.calculate_average_scores_over_time(
            self.all_patients_data, self.all_patients_scores
        )

        return avg_data

    def get_line_chart(self, data, title, scores_map):
        logger.debug(f"get line chart for {title}")
        score_names = sorted(list(scores_map.keys()))

        fig = px.line(
            data,
            x=SEQ,
            y=score_names,
            title=title,
            markers=True,
            labels={"SEQ": "Survey Time Period", "y": "Score", "value": "Score"},
        )

        self.fix_xaxis(fig, data)
        self.fix_yaxis(fig)

        def get_legend_group(name):
            return "average_group" if name.startswith("avg_") else "patient_group"

        def get_legend_group_title(name):
            d = {
                "average_group": "Average Values Over All Patients",
                "patient_group": "Individual Patient Values",
            }
            return d[get_legend_group(name)]

        def get_opacity(name):
            return 0.3 if name.startswith("avg_") else 1.0

        scores_map["seq"] = "Survey Time Period"
        fig.for_each_trace(
            lambda t: t.update(
                name=scores_map[t.name],
                legendgroup=get_legend_group(t.name),
                legendgrouptitle_text=get_legend_group_title(t.name),
                opacity=get_opacity(t.name),
                line={"dash": "dash"}
                if t.name.startswith("avg_")
                else {"dash": "solid"},
                hovertemplate=t.hovertemplate.replace(t.name, scores_map[t.name]),
            )
        )

        if self.patient:
            id = f"sgc-line-chart-{title}-{self.patient.id}"
        else:
            id = f"sgc-line-chart-{title}-all"

        if self.better is not None:
            logger.debug(f"adding indicator better is {self.better}")
            self.add_indicator(fig, data)
        else:
            logger.debug("self.better is None no indicator added?")
        div = html.Div([dcc.Graph(figure=fig)], id=id)
        return div

    def add_indicator(self, fig, data):
        import math

        logger.debug(f"add indicator: {self.better}")
        image_src = self.better_indicator_image(self.better)
        r, _ = data.shape
        logger.debug(f"num collection dates = {r}")

        x_pos = math.floor(0.5 * r)
        if x_pos == 0:
            x_pos = 0.50

        logger.debug(f"x_pos = {x_pos}")
        x_size = math.floor(0.1 * r)
        if x_size == 0:
            x_size = 0.5
        y_size = 30

        logger.debug(f"x_pos = {x_pos} x_size = {x_size} y_size = {y_size}")

        if self.better == "up":
            self.add_image(fig, image_src, x_pos, 80, x_size, y_size, opacity=0.5)
        elif self.better == "down":
            self.add_image(fig, image_src, x_pos, 40, x_size, y_size, opacity=0.5)

    def get_table(self, data, scores_map):
        import plotly.graph_objects as go

        # data frame looks like
        #       PID     SEQ      TYPE  ...      SEQ_NAME    score_0    score_1
        #  0    1032    0  baseline  ...      Baseline  23.809524  54.166667
        #  1    1032    1  followup  ...  1st Followup  37.500000  29.166667
        #  2    1032    2  followup  ...  2nd Followup  45.833333  33.333333
        #  3    1032    3  followup  ...  3rd Followup  75.000000  83.333333

        # they want (e.g.):

        # scale group name    baseline 1st followup  2nd followup ...
        # Functional           34.4       45.9         55.99
        # Cognitive etc        23.5       0.5          10.0

        # With Symptom and QOL/Health Score, the spec has a comparison
        # with the average score for all patients, if so avg_score_
        # columns will have already been added

        def score_names():
            for k in scores_map:
                if k.startswith("score_") or k.startswith("avg_score_"):
                    yield k

        columns_required = ["SEQ_NAME"] + [score_name for score_name in score_names()]
        df = data[columns_required].round(1)

        columns = []

        def get_scale_group_name(k):
            if k.startswith("avg_score"):
                j = k.replace("avg_", "")
                return "Average " + self.group_info[j]
            else:
                return self.group_info[k]

        scale_group_col = [get_scale_group_name(k) for k in score_names()]
        columns.append(scale_group_col)

        for index, row in df.iterrows():
            columns.append([row[k] for k in score_names()])

        headers = ["Scale Group"] + list(data["SEQ_NAME"])

        def remove_date(h):
            if "(" in h:
                return h[: h.find(" (")]
            else:
                return h

        headers = [remove_date(h) for h in headers]

        fig = go.Figure(
            data=[go.Table(header=dict(values=headers), cells=dict(values=columns))]
        )
        div = html.Div([dcc.Graph(figure=fig)], id="fkdflkdfdf")
        return div

    def calculate_average_scores_over_time(self, data, score_names):
        # this only makes sense if this chart is passed
        # all patients scores
        aggregations_map = {score_name: "mean" for score_name in score_names}

        df = data.groupby(SEQ).agg(aggregations_map).reset_index()
        return df

    def get_scale(self):
        return self.config.get("scale", None)

    def calculate_scores(self, score_name, fields, score_function, data):
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

        logger.debug(f"{score_name} delta = {delta}")

        def filled(value):
            # non vectorised
            return value not in [None, ""]

        def rs(row):
            # non vectorised
            values = [
                float(row[field]) + delta for field in fields if filled(row[field])
            ]
            n = len(values)
            if n == 0:
                return None
            else:
                avg = sum(values) / len(values)

            return avg

        def vec_rs(df):
            # vectorised
            # problem here is the empty values propagate NA?
            values = [pd.to_numeric(df[field]) + delta for field in fields]
            avg = sum(values) / len(values)
            return avg

        from datetime import datetime

        start_time = datetime.now()
        # unvectorised
        data[score_name] = data.apply(lambda row: score_function(rs(row)), axis=1)

        # vectorised
        # data[score_name] = score_function(vec_rs(data))

        end_time = datetime.now()

        logger.info(
            f"score {score_name} time = {(end_time - start_time).total_seconds() } seconds"
        )

        return data

    def get_score_function(self, range_value, scale):
        if scale == "functional":
            log("scale is functional")

            def score(rs):
                # rs: raw score = average of values
                if rs is None:
                    return None
                s = (1.0 - (rs - 1.0) / range_value) * 100.0
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
        for field in fields:
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

    def load_all_patients_data(self):
        if not self.all_patients_data:
            from rdrf.models.definition.models import Registry
            from dashboards.data import get_data

            registry = Registry.objects.get()
            self.all_patients_data = get_data(registry)
