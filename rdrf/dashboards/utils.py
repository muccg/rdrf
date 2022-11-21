from rdrf.models.definition.models import Registry
from registry.patients.models import Patient


class PromsType:
    baseline = "baseline"
    follow_up = "follow_up"


class Proms:
    """
    Wrapper to make it easier to work with baseline and followup
    patient reported outcomes.
    """

    def __init__(self, registry, patient, clinical_data):
        self.registry = registry
        self.patient = patient
        self.cd = clinical_data
        self.collection_date = None
        self.proms_type = None
        self._load()

    def _load(self):
        pass


def get_colour_map():
    orange = "#FFA500"

    color_discrete_map = {
        "Not at all": "green",
        "A little": "lightgreen",
        "Quite a bit": "orange",
        "Very much": "red",
    }
    return color_discrete_map
