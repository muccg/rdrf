import logging
from django.urls import reverse
from intframework.models import HL7Mapping, HL7Message
from intframework.utils import get_event_code
from intframework.utils import parse_demographics_moniker
from rdrf.db.contexts_api import RDRFContextManager
from rdrf.models.definition.models import Registry
from registry.groups.models import WorkingGroup
from registry.patients.models import Patient
from typing import Optional, Tuple

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

    def _get_update_dict(self, registry_code: str) -> Tuple[Optional[dict], HL7Message]:
        event_code = get_event_code(self.hl7message)

        try:
            patient = Patient.objects.get(umrn=self.umrn)
        except Patient.DoesNotExist:
            patient = None
        try:
            hl7_mapping = HL7Mapping.objects.get(event_code=event_code)
            update_dict, message_model = hl7_mapping.parse(self.hl7message, patient, registry_code)
            return update_dict, message_model
        except HL7Mapping.DoesNotExist:
            message = f"mapping doesn't exist Unknown message event code: {event_code}"
            logger.error(message)
            message_model.error_message = message
            message_model.save()
            return None, message_model
        except HL7Mapping.MultipleObjectsReturned:
            message = f"Multiple message mappings for event code: {event_code}"
            logger.error(message)
            message_model.error_message = message
            message_model.save()
            return None, message_model

    def _update_patient(self) -> Optional[Patient]:
        patient = None
        try:
            patient = Patient.objects.get(umrn=self.umrn)
        except Patient.DoesNotExist:
            return None
        updated = Patient.objects.filter(pk=patient.id).update(**self.patient_attributes)
        if updated:
            return patient
        return None

    def handle(self) -> Optional[dict]:
        logger.info("updating or creating patient from hl7 message data")
        registry = Registry.objects.get()
        patient = None
        try:
            field_dict, message_model = self._get_update_dict(registry.code)
            if field_dict is None:
                logger.error("field_dict is None")
                return None
            self.patient_attributes = self._parse_field_dict(field_dict)
            umrn = self.patient_attributes["umrn"]
            logger.info(f"umrn = {umrn}")
            if self._umrn_exists(umrn):
                logger.info("A patient already exists with this umrn so updating")
                patient = self._update_patient()
                if patient:
                    self.patient_attributes["patient_updated"] = "updated"
                    message_model.patient_id = patient.id
                    message_model.umrn = umrn
                    message_model.state = "R"
                    message_model.save()
                    logger.info("message model updated ok")

            else:
                logger.info(f"No patient exists with umrn: {umrn}: a new patient will be created")
                patient = Patient(**self.patient_attributes)
                patient.consent = False
                patient.save()
                logger.info(f"patient saved ok umrn = {umrn} id = {patient.id}")
                message_model.patient_id = patient.id
                message_model.umrn = umrn
                message_model.state = "R"
                message_model.save()
                logger.info("message model updated ok")
                patient.rdrf_registry.set([registry])
                wg = WorkingGroup.objects.get(registry=registry)
                patient.working_groups.set([wg])
                patient.save()
                logger.info("patient working group set")
                logger.info("patient registry  set")
                context_manager = RDRFContextManager(registry)
                default_context = context_manager.get_or_create_default_context(patient, new_patient=True)
                logger.info("default_context created")
                self._populate_pmi(registry.code, patient, umrn, default_context)
                logger.info("pmi populated with urmrn")
        except Exception as ex:
            logger.error(f"Error creating patient: {ex}")
            return None

        if hasattr(patient, "pk"):
            self.patient_attributes["patient_url"] = reverse("patient_edit",
                                                             args=[registry.code, patient.pk])
        else:
            self.patient_attributes["patient_url"] = ""
        return self.patient_attributes
