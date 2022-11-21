from dash import dcc, html
from ..components.cpr import ChangesInPatientResponses


class FieldGroupComparison(ChangesInPatientResponses):
    def perform_calculation(self, field: str, config: dict):

        """
        Return a calculation column based on config dict
        """
        pass
