import logging
import pandas as pd
import plotly.express as px
from dash import dcc, html
from ..components.common import BaseGraphic
from ..utils import get_colour_map


logger = logging.getLogger(__name__)


def log(msg):
    logger.debug(f"sgc: {msg}")


SEQ = "SEQ"


class ScaleGroupComparison(BaseGraphic):
    def get_graphic(self):
        log("creating Scale Group Comparison")
        fields = [field["code"] for field in self.config["fields"]]

        self.data = self._calculate_scores(fields, self.data)

        div = html.Div([html.H3(self.title)])
        return html.Div(div, id="sgc")

    def _calculate_scores(self, fields, data):
        score_function = self._get_scoring_function()
        data["score"] = data.apply(lambda row: score_function(fields, row), axis=1)
        return data

    def _get_score_function(self):
        score_function_name = self.config.get("score_function", "eortc")
        if score_function_name == "eortc":
            return self._eortc_score
        else:
            raise NotImplemented()

    def _eortc_score(self, fields, row):
        # MeasureScaleScore3 =
        # IF (NOT (ISBLANK(patients_data[AvgScale])),
        #    (1-(([AvgScale]-1))/3)*100)
        # //Creates Patients Measure Score utilising EORTC QLQ-C30 Scoring Manual methodology for Function-based survey responses
        def v(db_value):
            if db_value == "":
                return None
            else:
                try:
                    return int(db_value)
                except:
                    return None

            values = [v(row[field]) for field in fields]
            non_blank = [x for x in values if not x is None]
            avg = sum(non_blank) / len(non_blank)
            return 1.0 - ((avg - 1.0) / 3.0)
