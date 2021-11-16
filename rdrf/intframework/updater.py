import logging
from django.urls import reverse
from django.urls import NoReverseMatch
from intframework.models import HL7Mapping, HL7Message
from intframework.utils import get_event_code
from intframework.utils import get_umrn
from intframework.utils import parse_demographics_moniker
from rdrf.models.definition.models import Registry
from rdrf.models.definition.models import RegistryForm
from rdrf.models.definition.models import Section
from rdrf.models.definition.models import CommonDataElement
from registry.groups.models import WorkingGroup
from registry.patients.models import Patient
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def parse_cde_triple(key: str) -> Optional[Tuple[RegistryForm,
                                                 Section,
                                                 CommonDataElement]]:

    parts = key.split("/")

    if len(parts) != 3:
        logger.error(f"parse_cde_triple: not enough parts {key}")
        return None

    form_name, section_code, cde_code = parts

    try:
        form_model = RegistryForm.objects.get(name=form_name)
    except RegistryForm.DoesNotExist:
        logger.error(f"parse cde triple: {form_name} is not a form")
        return None
    except RegistryForm.MultipleObjectsReturned:
        logger.error(f"parse cde triple: multiple {form_name}")

    try:
        section_model = Section.objects.get(code=section_code)
    except Section.DoesNotExist:
        logger.error(f"parse cde triple: {section_code} is not a section")
        return None
    except Section.MultipleObjectsReturned:
        logger.error(f"parse cde triple: multiple {section_code}")

    try:
        cde_model = CommonDataElement.objects.get(code=cde_code)
    except CommonDataElement.DoesNotExist:
        logger.error(f"parse cde triple: {cde_code} is not a cde")
        return None
    except CommonDataElement.MultipleObjectsReturned:
        logger.error(f"parse cde triple: multiple {cde_code}")
        return None

    if section_model not in form_model.section_models:
        logger.error(f"parse cde triple: {section_code} not in form {form_name}")
        return None

    if cde_model not in section_model.cde_models:
        logger.error(f"parse cde triple: {cde_code} not in form {section_code}")
        return None

    return form_model, section_model, cde_model


class HL7Handler:
    def __init__(self, *args, **kwargs):
        self.umrn = kwargs.get("umrn", None)
        self.hl7message = kwargs.get("hl7message", None)
        self.username = kwargs.get("username", "unknown")

    def _get_mapping(self, event_code):
        try:
            mapping = HL7Mapping.objects.get(event_code=event_code)
            logger.info(f"found mapping for {event_code}")
            return mapping
        except HL7Mapping.DoesNotExist:
            try:
                logger.error(f"No mapping for event code {event_code}")
                fallback_mapping = HL7Mapping.objects.get(event_code="fallback")
                logger.info(f"using fallback mapping instead of {event_code}")
                return fallback_mapping
            except HL7Mapping.DoesNotExist:
                logger.error("No fallback mapping defined on the site")
                raise

    def _parse_demographics_fields(self, field_dict) -> dict:
        field_values = {}
        for key, value in field_dict.items():
            if self._is_demographics_field(key):
                field_name = parse_demographics_moniker(key)
                if field_name:
                    field_values[field_name] = value
        return field_values

    def _parse_cde_fields(self, field_dict) -> dict:
        field_values = {}
        for key, value in field_dict.items():
            if not self._is_demographics_field(key):
                cde_triple = parse_cde_triple(key)
                if cde_triple is not None:
                    field_values[cde_triple] = value
        return field_values

    def _is_demographics_field(self, key):
        return key.startswith("Demographics/")

    def _populate_pmi(self, registry_code: str, patient: Patient, umrn: str, default_context):
        form_name = "Patientinformation"
        section_code = "PtIdentifiers1"
        cde_code = "PMI"
        patient.set_form_value(registry_code, form_name, section_code, cde_code, umrn, context_model=default_context)

    def _umrn_exists(self, umrn: str) -> bool:
        return Patient.objects.filter(umrn=umrn).count() > 0

    def _get_update_dict(self, registry_code: str) -> Tuple[Optional[dict], HL7Message]:
        event_code = get_event_code(self.hl7message)
        message_model = self._create_message_model(registry_code, self.hl7message)

        try:
            patient = Patient.objects.get(umrn=self.umrn)
        except Patient.DoesNotExist:
            patient = None
        try:
            hl7_mapping = self._get_mapping(event_code)
            update_dict, message_model = hl7_mapping.parse(self.hl7message, patient, registry_code, message_model)
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
        except Exception as ex:
            message = f"Unhandled error: {ex}"
            message_model.error_message = message
            message_model.save()
            return None, message_model

    def _create_message_model(self, registry_code, message):
        event_code = get_event_code(message)
        umrn = get_umrn(message)
        message_model = HL7Message(username="HL7Updater",
                                   event_code=event_code,
                                   content=message,
                                   umrn=umrn,
                                   registry_code=registry_code)
        message_model.save()
        return message_model

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

    def _update_cdes(self, registry, patient):
        from registry.groups.models import CustomUser
        default_context = patient.default_context(registry)

        if self.username in ["updater", "testing"]:
            user_model = CustomUser.objects.get(username="admin")
        else:
            try:
                user_model = CustomUser.objects.get(username=self.username)
            except CustomUser.DoesNotExist:
                raise Exception("unknown user")

        for cde_triple, value in self.patient_cdes.items():
            form_model, section_model, cde_model = cde_triple
            patient.set_form_value(registry.code,
                                   form_model.name,
                                   section_model.code,
                                   cde_model.code,
                                   value,
                                   default_context,
                                   save_snapshot=True,
                                   user=user_model)

    def handle(self) -> Optional[dict]:
        logger.info("updating or creating patient from hl7 message data")
        registry = Registry.objects.get()
        patient = None
        umrn = None
        try:
            field_dict, message_model = self._get_update_dict(registry.code)
            if field_dict is None:
                logger.error("field_dict is None")
                return {"error": "field_dict is None"}
            self.patient_attributes = self._parse_demographics_fields(field_dict)
            self.patient_cdes = self._parse_cde_fields(field_dict)
            umrn = self.patient_attributes["umrn"]
            logger.info(f"umrn = {umrn}")
            if self._umrn_exists(umrn):
                logger.info("A patient already exists with this umrn so updating")
                patient = self._update_patient()
                if patient:
                    self._update_cdes(registry, patient)
                    logger.info(f"patient updated ok umrn = {umrn} id = {patient.id}")
                    self.patient_attributes["patient_updated"] = "updated"
                    message_model.patient_id = patient.id
                    message_model.umrn = umrn
                    message_model.state = "R"
                    message_model.save()
            else:
                logger.info(f"No patient exists with umrn: {umrn}: a new patient will be created")
                patient = Patient(**self.patient_attributes)
                patient.consent = False
                patient.save()
                default_context = patient.get_or_create_default_context(registry)
                self._update_cdes(registry, patient)
                logger.info(f"patient saved ok umrn = {umrn} id = {patient.id}")
                message_model.patient_id = patient.id
                message_model.umrn = umrn
                message_model.state = "R"
                message_model.save()
                patient.rdrf_registry.set([registry])
                wg = WorkingGroup.objects.get(registry=registry)
                patient.working_groups.set([wg])
                patient.save()
                self._populate_pmi(registry.code, patient, umrn, default_context)
        except Exception as ex:
            logger.error(f"Error creating/updating patient {umrn}: {ex}")
            return {"Error creating/updating patient with UMRN": umrn,
                    "Exception": ex}

        self.patient_attributes["patient_url"] = ""
        if hasattr(patient, "pk"):
            try:
                self.patient_attributes["patient_url"] = reverse("externaldemographics",
                                                                 args=[registry.code, patient.pk])
            except NoReverseMatch:
                pass

        return self.patient_attributes
