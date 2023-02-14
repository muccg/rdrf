from dash import dcc, html
import dash_bootstrap_components as dbc
from rdrf.models.definition.models import Registry
from rdrf.models.definition.models import RegistryForm
from rdrf.models.definition.models import Section
from rdrf.models.definition.models import CommonDataElement
from ..components.common import BaseGraphic
from ..data import missing_data_all_forms
import logging

logger = logging.getLogger(__name__)


class MissingDataReport(BaseGraphic):
    def get_graphic(self):
        logger.debug("in missing data report")

        registry = Registry.objects.get()
        data = missing_data_all_forms(self.patient, registry)
        table = self.get_table(data)
        blurb = html.Div(
            "This table shows fields that have not been filled in for the patient."
        )

        return html.Div([blurb, table])

    def get_table(self, data):
        headers = ["Form", "Section", "Field"]
        table_header = [html.Thead(html.Tr([html.Th(h) for h in headers]))]
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
                row = html.Tr(
                    [
                        html.Td(form_display),
                        html.Td(section_display),
                        html.Td(cde_display),
                    ]
                )
                rows.append(row)

        table_body = [html.Tbody([*rows])]
        table = dbc.Table(table_header + table_body, bordered=True, striped=True)
        return table
