from ..components.common import BaseGraphic
import logging
import pandas as pd

logger = logging.getLogger(__name__)


def log(msg):
    logger.debug(f"fgc: {msg}")


SEQ = "seq"


class CombinedFieldComparison(BaseGraphic):
    def get_graphic(self):
        log("creating Combined Field Comparison")
        inputs = self.config("inputs")  # e.g. ["EORTCQLQC30_Q29","EORTCQLQC30_Q30"]
        title = self.config("title")
        data = self._get_combined_data(self.data, inputs)
        bars_div = self._create_bars_div(data, title, inputs)
        div = html.Div([html.H3(title), bars_div])
        log("created combined field comparision graphic")
        return html.Div(cpr_div, id="fgc")

    def _get_combined_data(self, df: pd.DataFrame, inputs) -> pd.DataFrame:
        df_counts = []
        num_inputs = len(inputs)
        for index, input in enumerate(inputs):
            input_df = df[[SEQ, input]].value_counts().reset_index()
            input_df.rename(columns={input: "value", 0: f"count_{index}"})
            df_counts.append(input_df)

        count_columns = ["count_{index}" for index in range(num_inputs)]

        merged = pd.merge(*df_counts, how="outer", on=[SEQ, "value"])
        merged["count"] = pd.Series.sum(
            [merged[count_column] for count_column in count_columns]
        )
        log(merged.columns)
        log(merged)
        return merged
