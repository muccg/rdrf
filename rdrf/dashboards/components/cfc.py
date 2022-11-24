import logging
import pandas as pd
import plotly.express as px
from dash import dcc, html
from ..components.common import BaseGraphic
from ..utils import get_colour_map


logger = logging.getLogger(__name__)


def log(msg):
    logger.debug(f"cfc: {msg}")


SEQ = "SEQ"


class CombinedFieldComparison(BaseGraphic):
    def get_graphic(self):
        log("creating Combined Field Comparison")
        inputs = self.config["inputs"]  # e.g. ["EORTCQLQC30_Q29","EORTCQLQC30_Q30"]
        log(f"inputs = {inputs}")
        colour_map = self.config.get("colour_map", None)
        data = self._get_combined_data(self.data, inputs)
        log(f"combined data  = {data}")
        bars_div = self._create_bars_div(data, inputs, colour_map)
        div = html.Div([html.H3(self.title), bars_div])
        log("created combined field comparision graphic")
        return html.Div(div, id="fgc")

    def _create_bars_div(self, data, inputs, colour_map):
        if colour_map is None:
            colour_map = get_colour_map()

        combined_name = self._get_combined_name(inputs)

        fig = px.bar(
            data,
            SEQ,
            "Percentage",
            color="value",
            barmode="stack",
            title=f"Change in {combined_name} over time for all patients",
            color_discrete_map=colour_map,
        )

        log("created bar")
        id = f"bar-combined"
        div = html.Div([dcc.Graph(figure=fig)], id=id)
        return div

    def _get_combined_name(self, inputs):
        return "Health Status/Quality of Life"

    def _get_combined_data(self, df: pd.DataFrame, inputs) -> pd.DataFrame:
        """
        This is turned out to be hard:)
        Basically we're looking at both Health Status and Quality of life
        and counting the responses as they use a common value group
        of 1 to 7. If there was only 1 patient filling in one response,
        and they answered 7 for both Health Status and Quality of Life,
        this would be a count of 2, so 100% 7.

        if in baseline ( seq = 0) this was the only data
        SEQ  PID  QOL HS
        0     1   7   1
        0     2   7   7

        this would mean the value 7 occurs 3 times
        in the group seq=0, value=7
        count_0 would be 2 ( qol of 7)
        count_1 would be 1
        count would be 3
        percentage of 7 in seq 0 is therefore 100.0 * 3/ 4 = 75%
        i.e. of the 2 x 2 slots in seq 0  3x are 7 and 1 slot of 4 is 1 (25%)

        The code here allows us to specify not just two inputs but many.
        the counts for each input(i.e. cde) ( called count_0 count_1 etc) are combined into one count
        column called "count" and then aggregated.

        I first work out the counts for one input , renaming the input(cde code) column
        to "value".
        Then the second etc.
        Each produces a dataframe of counts ( with count columns renamed to count_0
        count_1 etc)
        These are then merged on the SEQ and value columns to find corresponding rows
        This merged dataframe is then grouped and aggregated to get the percentage..
        maybe there is an easier way.
        """
        log(f"in get combined data")
        df_counts = []
        num_inputs = len(inputs)
        log(f"number of inputs = {num_inputs}")
        log(f"df = {df}")
        for index, input in enumerate(inputs):
            input_df = df[[SEQ, input]].value_counts().reset_index()
            input_df = input_df.rename(columns={input: "value", 0: f"count_{index}"})
            log(f"input {input} df columns = {input_df.columns}")
            log(f"input df for input {input}: {input_df}")

            df_counts.append(input_df)

        count_columns = [f"count_{index}" for index in range(num_inputs)]
        log(f"count columns = {count_columns}")

        merged = pd.merge(*df_counts, how="outer", on=[SEQ, "value"])
        merged = merged.fillna(0)
        log(f"merged df columns = {merged.columns}")
        log(f"merged data frame = \n{merged}")
        merged["count"] = sum([merged[count_column] for count_column in count_columns])

        log(f"merged with count column:\n{merged}")

        # count the total number of  value counts per seq
        counted = merged.groupby(["SEQ", "value"])[["count"]].agg({"count": "sum"})
        # for each seq, work out the percentage of that value compared to the total count of the seq
        counted["Percentage"] = (
            100.0 * counted["count"] / counted.groupby("SEQ")["count"].sum()
        )

        log(f"counted df = {counted}")
        # reset index
        counted = counted.reset_index()
        return counted
