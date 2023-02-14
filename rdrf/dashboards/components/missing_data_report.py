from dash import dcc, html
import plotly.graph_objects as go
from rdrf.models.definition.models import Registry
from rdrf.models.definition.models import RegistryForm
from rdrf.models.definition.models import Section
from rdrf.models.definition.models import CommonDataElement
from ..components.common import BaseGraphic
from ..data import missing_data


class MissingDataReport(BaseGraphic):
    def get_graphic(self):

        registry = Registry.objects.get()
        baseline = self.patient.baseline
        data = missing_data(registry, self.patient, baseline)

        headers = ["Form", "Section", "Field"]
        rows = []

        for form_name, triples in data.items():
            for _, section_code, cde_code in triples:
                form_model = RegistryForm.objects.get(name=form_name)
                form_display = form_model.display_name

                section_model = Section.objects.get(code=section_code)
                section_display = section_model.display_name

                cde_model = CommonDataElement.objects.get(code=cde_code)
                cde_display = cde_model.name

                row = [form_display, section_display, cde_display]
                rows.append(row)

        fig = go.Figure(
            data=[go.Table(header=dict(values=headers), cells=dict(values=rows))]
        )
        div = html.Div([dcc.Graph(figure=fig)], id="missing-data")
        return div
