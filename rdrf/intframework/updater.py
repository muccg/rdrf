import logging
from intframework.models import HL7Mapping
from intframework.utils import parse_demographics_moniker
from rdrf.models.definition.models import Registry
from registry.groups.models import WorkingGroup
from registry.patients.models import Patient
from typing import Optional

logger = logging.getLogger(__name__)


class HL7Handler:
    def __init__(self, *args, **kwargs):
        self.umrn = kwargs.get("umrn", None)
        self.hl7message = kwargs.get("hl7message", None)

    def _parse_field_dict(self, field_dict) -> dict:
        field_values = {}
        for key, value in self.field_dict.items():
            field_name = parse_demographics_moniker(key)
            if field_name:
                field_values[field_name] = value
        return field_values

    def _populate_pmi(self, regsitry_code: str, patient: Patient, umrn: str):
        form_name = "Patientinformation"
        section_code = "PtIdentifiers1"
        cde_code = "PMI"
        patient.set_form_value(registry_code, form_name, section_code, cde_code, umrn)

    def _umrn_exists(self, umrn: str) -> bool:
        return Patient.objects.filter(umrn=umrn).count() > 0

    def create_patient(self, field_dict: dict) -> Optional[Patient]:
        logger.debug("creating patient ...")
        try:
            patient_attributes = self._parse_field_dict(field_dict)
            umrn = patient_attributes["umrn"]
            if self._umrn_exists():
                raise Exception(f"Patient with this UMRN {umrn} exists")
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
        self._populate_pmi(registry.code, patient, umrn)
        return patient

    def update_patient(self) -> Patient:
        patient = Patient.objects.get(umrn=self.umrn)
        hl7_mapping = HL7Mapping.objects.get()
        field_dict = hl7_mapping.parse(self.hl7message)
        field_values = self._parse_field_dict(field_dict)
        updated = Patient.objects.filter(pk=patient.id).update(**field_values)
        result = "failure"
        if updated:
            result = "success"
        return result
