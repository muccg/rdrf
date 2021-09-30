from registry.patients.models import Patient
# from rdrf.models import *
# from rdrf.models.definition.models import *
from registry.patients.models import Patient
from registry.groups.models import WorkingGroup


class IntegrationTool:
    def __init__(self):
        pass

    def process(self, hl7_message):
        pass

    def _parse_moniker(self, moniker):
        field = None
        if "/" in moniker:
            _, field = moniker.split("/")
        return field

    def parse_map(self, value_map: dict):
        field_values = {}
        for key, value in value_map.items():
            field_name = self._parse_moniker(key)
            if field_name:
                field_values[field_name] = value
        return field_values

    """
    the creation map keys:
    "Demographics/family_name"
    "Demographics/given_names"
    "Demographics/umrn"
    "Demographics/date_of_birth"
    "Demographics/date_of_death"
    "Demographics/place_of_birth"
    "Demographics/country_of_birth"
    "Demographics/ethnic_origin"
    "Demographics/sex"
    "Demographics/home_phone"
    "Demographics/work_phone"
    """

    def create_patient(self, value_map: dict):
        patient_attributes = self.parse_map(value_map)
        patient = Patient(**patient_attributes)
        patient.consent = True
        patient.active = True
        patient.save()

        registry = Registry.objects.get(registry_code=value_map[registry_code])
        p.rdrf_registry.set([registry])
        wg = WorkingGroup.objects.get(name=value_map[name], registry=registry)
        p.working_groups.set([wg])
        p.save()
