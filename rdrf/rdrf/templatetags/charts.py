from django import template
from django.utils.html import escapejs

import json
register = template.Library()


class ChartNode(template.Node):

    def __init__(self, chart_type, chart_id_variable, data_variable):
        self.chart_type = chart_type
        self.chart_id = template.Variable(chart_id_variable)
        self.data_variable = template.Variable(data_variable)

    def render(self, context):
        # the data to written as json for the chart wrapper
        data = self.data_variable.resolve(context)
        chart_data_json = escapejs(json.dumps(data))
        canvas_id = self.chart_id.resolve(context)
        chart_method = "Bar"
        if self.chart_type == "pie_chart":
            chart_method = "Pie"

        # create a chart using Chart.js
        # NB the curly brace escapes to please .format
        # NB a closure is created to avoid variable name clashes
        html = """<script>
                        (function() {{
                            var chartDataJSON = "{chart_data_json}";
                            var chartData = jQuery.parseJSON(chartDataJSON);
                            $(document).ready(function() {{
                                var ctx = $("#{canvas_id}")[0].getContext("2d");
                                window.my{chart_method} = new Chart(ctx).{chart_method}(chartData, {{
                                    responsive : false
                                }})
                            }})
                        }})();
                    </script>
                    <div width="100%">
                        <canvas id="{canvas_id}" height="200" width="200"></canvas>
                    </div>"""

        return html.format(canvas_id=canvas_id, chart_method=chart_method, chart_data_json=chart_data_json)


def create_chart_node(parser, token):
    chart_type_name, chart_id_variable, data_variable = token.split_contents()
    return ChartNode(chart_type_name, chart_id_variable, data_variable)


register.tag('bar_chart', create_chart_node)
register.tag('pie_chart', create_chart_node)
