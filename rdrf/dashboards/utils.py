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


def get_proms(registry: Registry, patient: Patient) -> List[Response]:
    cds = ClinicalData.objects.filter(django_id=patient.id, collection="cdes").order_by(
        "created"
    )

    return sorted([ Proms(registry, patient, cd) for cd in cds,
                    key=lambda p: p.collection_date])
        
