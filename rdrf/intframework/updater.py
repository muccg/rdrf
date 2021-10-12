import logging
from intframework.models import HL7Mapping
from intframework.utils import get_event_code
from intframework.utils import parse_demographics_moniker
from rdrf.db.contexts_api import RDRFContextManager
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
        for key, value in field_dict.items():
            field_name = parse_demographics_moniker(key)
            if field_name:
                field_values[field_name] = value
        return field_values

    def _populate_pmi(self, registry_code: str, patient: Patient, umrn: str, default_context):
        form_name = "Patientinformation"
        section_code = "PtIdentifiers1"
        cde_code = "PMI"
        patient.set_form_value(registry_code, form_name, section_code, cde_code, umrn, context_model=default_context)

    def _umrn_exists(self, umrn: str) -> bool:
        return Patient.objects.filter(umrn=umrn).count() > 0

    def _get_update_dict(self) -> Optional[dict]:
        event_code = get_event_code(self.hl7message)
        try:
            hl7_mapping = HL7Mapping.objects.get()
            update_dict = hl7_mapping.parse(self.hl7message)
            return update_dict
        except HL7Mapping.DoesNotExist:
            logger.error(f"mapping doesn't exist Unknown message event code: {event_code}")
            return None
        except HL7Mapping.MultipleObjectsReturned:
            logger.error("Multiple message mappings for event code: {event_code}")
            return None

    def _update_patient(self) -> Optional[Patient]:
        patient = Patient.objects.get(umrn=self.umrn)
        updated = Patient.objects.filter(pk=patient.id).update(**self.patient_attributes)
        if updated:
            return patient
        return None

    def handle(self) -> Optional[Patient]:
        logger.debug("creating patient ...")
        try:
            field_dict = self._get_update_dict()
            logger.debug(f"{field_dict}")
            self.patient_attributes = self._parse_field_dict(field_dict)
            logger.debug(f"{self.patient_attributes}")
            umrn = self.patient_attributes["umrn"]
            if self._umrn_exists(umrn):
                patient = self._update_patient()
            else:
                patient = Patient(**self.patient_attributes)
                patient.consent = False
                patient.save()
                logger.debug(f"patient created!: {patient.id} {patient} {patient.umrn} ")
                registry = Registry.objects.get()
                patient.rdrf_registry.set([registry])
                wg = WorkingGroup.objects.get(registry=registry)
                patient.working_groups.set([wg])
                patient.save()
                context_manager = RDRFContextManager(registry)
                default_context = context_manager.get_or_create_default_context(patient, new_patient=True)
                # patient.save()
                self._populate_pmi(registry.code, patient, umrn, default_context)
        except Exception as ex:
            logger.error(f"Error creating patient: {ex}")
            return None

        return self.patient_attributes
