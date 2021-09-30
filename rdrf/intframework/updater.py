from registry.patients.models import Patient
from rdrf.models.definition.models import Registry
from registry.groups.models import WorkingGroup


class PatientCreator:
    def __init__(self):
        pass

    def _parse_moniker(self, moniker: str) -> str:
        field = None
        if "/" in moniker:
            _, field = moniker.split("/")
        return field

    def _parse_map(self, value_map: dict) -> dict:
        field_values = {}
        for key, value in value_map.items():
            field_name = self._parse_moniker(key)
            if field_name:
                field_values[field_name] = value
        return field_values

    """
    the creation value map keys:
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

    def create_patient(self, value_map: dict) -> Patient:
        patient_attributes = self._parse_map(value_map)
        patient = Patient(**patient_attributes)
        patient.consent = False
        patient.save()

        registry = Registry.objects.get()
        patient.rdrf_registry.set([registry])
        wg = WorkingGroup.objects.get(registry=registry)
        patient.working_groups.set([wg])
        patient.save()

        return patient


class PatientUpdator:
    def __init__(self):
        pass

    # TODO: this class to be used for subscription updates
