import logging
from rdrf.helpers.utils import check_models
from rdrf.models.definition.models import Registry
from registry.groups.models import WorkingGroup
from registry.patients.models import Patient
from typing import Optional

logger = logging.getLogger(__name__)


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

    def create_patient(self, value_map: dict) -> Optional[Patient]:
        logger.debug("creating patient ...")
        try:
            patient_attributes = self._parse_map(value_map)
            patient = Patient(**patient_attributes)
            patient.consent = False
            patient.save()
            logger.debug(f"patient created!: {patient.id} {patient} {patient.umrn} ")
        except Exception as ex:
            logger.error(f"Error creating patient: {ex}")
            return None

        registry = Registry.objects.get()
        patient.rdrf_registry.set([registry])
        wg = WorkingGroup.objects.get(registry=registry)
        patient.working_groups.set([wg])
        patient.save()

        return patient


class PatientUpdator:
    """
    For HL7 subscription updates
    """

    def __init__(self, patient: Patient, value_map: dict):
        self.patient = patient
        self.value_map = value_map

    def _parse_moniker(self, moniker: str):
        form = None
        section = None
        cde = None
        if "/" in moniker:
            form, section, cde = moniker.split("/")
        return form, section, cde

    def _parse_map(self) -> list:
        cde_dicts = []
        for key, value in self.value_map.items():
            form, section, cde = self._parse_moniker(key)
            if form:
                cde_dicts.append({"form": form, "section": section, "cde": cde, "value": value})
        return cde_dicts

    def _set_cde_values(self, cde_dicts: dict()):
        registry = Registry.objects.get()
        registry_code = registry.code
        context = self.patient.default_context()
        for cde_dict in cde_dicts:
            form_name = cde_dict["form"]
            section_code = cde_dict["section"]
            cde_code = cde_dict["cde"]
            value = cde_dict["value"]

            self.patient.set_form_value(registry_code,
                                        form_name,
                                        section_code,
                                        cde_code,
                                        value,
                                        context_model=context)

    def update_patient(self) -> Patient:
        cde_dicts = self._parse_map()
        self._set_cde_values(cde_dicts)
        return self.patient
