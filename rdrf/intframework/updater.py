import sys
import logging
from django.urls import reverse
from django.urls import NoReverseMatch
from intframework.models import HL7Mapping, HL7Message
from intframework.utils import get_event_code
from intframework.utils import get_umrn
from intframework.utils import parse_demographics_moniker
from intframework.utils import empty_value_for_field
from rdrf.models.definition.models import Registry
from rdrf.models.definition.models import RegistryForm
from rdrf.models.definition.models import Section
from rdrf.models.definition.models import CommonDataElement
from registry.groups.models import WorkingGroup
from registry.patients.models import Patient
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def get_error_string(ex):
    # one of the errors we saw had a blank
    # message so hard to diagnose
    return f"Error: {ex}\nError Rep: {repr(ex)}"


def save_content(model, message):
    should_log = False
    try:
        model.content = message
        model.save()
        logger.info(f"saved message content to model {model.id} OK")
        return model
    except Exception as ex:
        should_log = True
        logger.error(f"could not save message content to model: {get_error_string(ex)}")

    logger.info("tring to save message using str")
    try:
        model.content = str(message)
        model.save()
        logger.info(f"saved message content to model {model.id} OK")
        return model
    except Exception as ex:
        should_log = True
        logger.error(f"could not save message content to model: {get_error_string(ex)}")

    if should_log:
        try:
            logger.info("Message content couldn't be logged on model.")
            logger.error(f"Bad Message content:{message}")
        except Exception as ex:
            logger.error(f"Could not write out message log: {get_error_string(ex)}")
    return model


def parse_cde_triple(
    key: str,
) -> Optional[Tuple[RegistryForm, Section, CommonDataElement]]:

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
            logger.error(f"No mapping for event code {event_code}")
            raise

    def _parse_demographics_fields(self, field_dict) -> dict:
        field_values = {}
        for key, value in field_dict.items():
            if value == '""':
                value = empty_value_for_field(key)
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

    def _populate_pmi(
        self, registry_code: str, patient: Patient, umrn: str, default_context
    ):
        form_name = "Patientinformation"
        section_code = "PtIdentifiers1"
        cde_code = "PMI"
        patient.set_form_value(
            registry_code,
            form_name,
            section_code,
            cde_code,
            umrn,
            context_model=default_context,
        )

    def _umrn_exists(self, umrn: str) -> bool:
        return Patient.objects.filter(umrn=umrn).count() > 0

    def _get_update_dict(
        self, registry_code: str
    ) -> Tuple[Optional[dict], Optional[HL7Message]]:
        event_code = get_event_code(self.hl7message)
        message_model = None

        logger.info("trying to create message model ...")
        try:
            message_model = self._create_message_model(registry_code, self.hl7message)
            message_model.save()
            logger.info("saved message model ok")
        except Exception as ex:
            logger.error("failed to create message model:", exc_info=sys.exc_info())
            logger.error(get_error_string(ex))

        try:
            patient = Patient.objects.get(umrn=self.umrn)
        except Patient.DoesNotExist:
            patient = None
        try:
            hl7_mapping = self._get_mapping(event_code)
            update_dict, message_model = hl7_mapping.parse(
                self.hl7message, patient, registry_code, message_model
            )
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
            message = f"Unhandled error: {get_error_string(ex)}"
            message_model.error_message = message
            message_model.save()
            return None, message_model

    def _create_message_model(self, registry_code, message):
        # need to ensure we can save the message with content
        logger.info("creating message model ...")
        try:
            logger.info("getting event code from message ...")
            event_code = get_event_code(message)
            logger.info("got event code")
        except Exception as ex:
            logger.error(f"Error getting event code: {get_error_string(ex)}")
            logger.info("setting event_code to 'error'")
            event_code = "error"

        try:
            logger.info("getting umrn from message ...")
            umrn = get_umrn(message)
            logger.info(f"got umrn")
            logger.info(f"umrn in message = {umrn}")

        except Exception as ex:
            logger.error(f"Error getting umrn from message: {get_error_string(ex)}")
            logger.info(f"setting umrn to empty string")
            umrn = ""

        if not umrn:
            logger.info(
                f"couldn't get umrn from message so using umrn from updater: {self.umrn}"
            )
            umrn = self.umrn

        message_model = HL7Message(
            username="HL7Updater",
            event_code=event_code,
            content="initial",
            umrn=umrn,
            registry_code=registry_code,
        )

        logger.info("saving model ..")
        try:
            message_model.save()
        except Exception as ex:
            logger.error(
                f"Error saving message model: {get_error_string(ex)}",
                exc_info=sys.exc_info(),
            )
            raise
        logger.info(f"saved message model pk = {message_model.pk}")

        logger.info("now trying to saving message content to model")

        save_content(message_model, message)

        return message_model

    def _update_patient(self) -> Optional[Patient]:
        patient = None
        try:
            patient = Patient.objects.get(umrn=self.umrn)
        except Patient.DoesNotExist:
            return None
        updated = Patient.objects.filter(pk=patient.id).update(
            **self.patient_attributes
        )
        if updated:
            logger.info("patient model updated")
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
            patient.set_form_value(
                registry.code,
                form_model.name,
                section_model.code,
                cde_model.code,
                value,
                default_context,
                save_snapshot=True,
                user=user_model,
            )

    def handle(self) -> Optional[dict]:
        logger.info("updating or creating patient from hl7 message data")
        registry = Registry.objects.get()
        patient = None
        umrn = self.umrn
        new_patient = None
        try:
            logger.info("creating message model and field dict ...")
            field_dict, message_model = self._get_update_dict(registry.code)
            if message_model is not None:
                mm = message_model.id
            else:
                mm = None
            if field_dict is None:
                logger.error(f"field_dict is None. message_model {mm}")
                return {
                    "error": "field_dict is None",
                    "message_model": mm,
                    "where": "getting field_dict",
                }

            logger.info("getting patient attributes...")
            self.patient_attributes = self._parse_demographics_fields(field_dict)
            logger.info("getting patient cdes...")
            self.patient_cdes = self._parse_cde_fields(field_dict)
            if not umrn:
                logger.info("no umrn from task - getting from attributes")
                umrn = self.patient_attributes.get("umrn", None)
                if umrn is None:
                    logger.info(
                        f"patient attributes doesn't have umrn: {self.patient_attributes}"
                    )
            logger.info(f"umrn = {umrn}")
            if not umrn:
                logger.error("UMRN missing or not parsed from patient attributes")
                return {
                    "error": "No UMRN couldn't update or create patient",
                    "umrn": str(umrn),
                    "message_model": mm,
                    "where": "getting umrn from patient attributes",
                }
            if self._umrn_exists(umrn):
                new_patient = False
                logger.info("A patient already exists with this umrn so updating ...")
                patient = self._update_patient()
                logger.info("patient updated")
                if patient:
                    logger.info("updating cdes ...")
                    self._update_cdes(registry, patient)
                    logger.info(
                        f"patient updated cdes ok umrn = {umrn} id = {patient.id}"
                    )
                    self.patient_attributes["patient_updated"] = "updated"
                    message_model.patient_id = patient.id
                    message_model.umrn = umrn
                    message_model.state = "R"
                    message_model.save()
            else:
                new_patient = True
                logger.info(
                    f"No patient exists with umrn: {umrn}: a new patient will be created"
                )
                patient = Patient(**self.patient_attributes)
                patient.consent = False
                patient.save()
                logger.info(f"new patient saved id = {patient.id}")
                default_context = patient.get_or_create_default_context(registry)
                self._update_cdes(registry, patient)
                logger.info(
                    f"new patient cdes saved ok umrn = {umrn} id = {patient.id}"
                )
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
            if new_patient is False:
                update_type = "updating existing patient"
            elif new_patient is True:
                update_type = "creating new patient"
            else:
                update_type = "determining patient"

            error_string = f"{get_error_string(ex)}"
            logger.error(f"Error in {update_type} patient {umrn}: {error_string}")

            return {
                "error": error_string,
                "umrn": str(umrn),
                "update_type": update_type,
                "where": "updating/creating patient",
            }

        logger.info("updater task succeeded - returning patient attributes")
        self.patient_attributes["patient_url"] = ""
        if hasattr(patient, "pk"):
            try:
                self.patient_attributes["patient_url"] = reverse(
                    "externaldemographics", args=[registry.code, patient.pk]
                )
            except NoReverseMatch:
                pass

        return self.patient_attributes
