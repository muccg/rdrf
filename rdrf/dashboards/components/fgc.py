from dashboards.components.common import BaseGraphic
from dash import dcc, html


def seq(data):
    names = {0: "Baseline", 1: "1st Follow Up", 2: "2nd Follow Up", 3: "3rd Follow Up"}

    yield 0, names[0]
    max_seq_num = data["seq"].max()
    for i in range(1, max_seq_num + 1):
        name = names.get(i, f"{i}th Follow Up")
        yield i, name


class FieldGroupComparison(BaseGraphic):
    """
    Calculate percentages of field groups
    for all baseline/followups
    """

    def get_graphic(self):
        bars = []
        for i, name in seq(self.data):
            percentages_dict = self._calculate_percentages(i)
            bar = self._create_bar_chart(name, percentages_dict)
            bars.append(bar)

        return html.H2("Field Comparison bars will go here")

    def _create_bar_chart(self, name, percentages_dict):
        return None

    def _calculate_percentages(self, index):
        pass
