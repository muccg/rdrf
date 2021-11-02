import hl7
import json
import logging
from django.conf import settings
from django.db import models
from intframework import utils
from intframework.utils import TransformFunctionError
from intframework.utils import MessageSearcher
from intframework.utils import NotFoundError
from intframework.utils import get_umrn
from typing import Tuple

logger = logging.getLogger(__name__)


class HL7:
    MESSAGE_TYPE_PATH = "MSH.F9.R1.C3"


class DataRequestState:
    REQUESTED = "REC"
    ERROR = "ERR"
    APPLIED = "APP"
    RECEIVED = "REC"


class HL7Message(models.Model):
    MESSAGE_STATES = (("C", "created"),
                      ("S", "sent"),
                      ("E", "error"))

    created = models.DateTimeField(auto_now_add=True)
    username = models.CharField(max_length=80)
    registry_code = models.CharField(max_length=80)
    content = models.TextField()
    state = models.CharField(choices=MESSAGE_STATES, max_length=1, default="C")
    error_message = models.TextField()  # save any error message on sending
    patient_id = models.IntegerField(null=True)
    umrn = models.CharField(max_length=50, null=True)
    event_code = models.CharField(max_length=10, default="")

    def parse(self):
        return hl7.parse(self.content)

    def valid(self):
        try:
            _ = self.parse()
            return True
        except hl7.exceptions.ParseException:
            return False

    @property
    def message_control_id(self):
        return f"{settings.APP_ID}.{self.registry_code}.{self.id}"


class HL7MessageFieldUpdate(models.Model):
    UPDATE_STATES = (("Success", "Success"),
                     ("Failure", "Failure"))

    created = models.DateTimeField(auto_now_add=True)
    hl7_message = models.ForeignKey(HL7Message, on_delete=models.CASCADE, related_name="updates")
    data_field = models.CharField(max_length=200, default="")
    hl7_path = models.CharField(max_length=20)
    original_value = models.CharField(max_length=200, default="")
    update_status = models.CharField(choices=UPDATE_STATES, max_length=10, default="Failure")
    failure_reason = models.CharField(max_length=300, default="", blank=True, null=True)


class HL7Mapping(models.Model):
    """
    Facilitate HL7 --> RDRF conversions
    """
    event_code = models.CharField(max_length=20)
    event_map = models.TextField(blank=True, null=True)

    def load(self):
        try:
            mapping_map = json.loads(self.event_map)
            return mapping_map
        except ValueError as ex:
            logger.error(f"Error loading HL7 mappings: HL7Mapping {self.id} {self.event_code}: {ex}")
            return {}

    def _get_event_code(self, parsed_message):
        return self._get_hl7_value(HL7.MESSAGE_TYPE_PATH, parsed_message)

    def _get_handler(self, tag):
        handler_name = f"_handle_{tag}"
        if hasattr(self, handler_name):
            return getattr(self, handler_name)
        else:
            raise Exception(f"Unknown tag: {tag}")

    def _handle_search(self, hl7_message, field_moniker, mapping_data, update_model):
        message_searcher = MessageSearcher(mapping_data)
        update_model.hl7_path = mapping_data["path"]
        transform = self._get_transform(mapping_data)
        hl7_value = message_searcher.get_value(hl7_message)
        rdrf_value = transform(hl7_value)
        update_model.original_value = hl7_value
        return rdrf_value

    def _handle_normal(self, hl7_message, field_moniker, mapping_data, update_model):
        transform_function = self._get_transform(mapping_data)
        hl7_path = mapping_data["path"]
        update_model.hl7_path = hl7_path
        hl7_value = self._get_hl7_value(hl7_path, hl7_message)
        update_model.original_value = hl7_value
        rdrf_value = transform_function(hl7_value)
        return rdrf_value

    def _handle_mapping(self, hl7_message, field_moniker, mapping_data, update_model):
        lookup_map = mapping_data.get("map", {})
        if not lookup_map:
            raise Exception(f"No map in mapping field for {field_moniker}")
        hl7_path = mapping_data["path"]
        update_model.hl7_path = hl7_path
        hl7_value = self._get_hl7_value(hl7_path, hl7_message)
        update_model.original_value = hl7_value
        rdrf_value = lookup_map[hl7_value]
        return rdrf_value

    def _handle_object(self, hl7_message, field_moniker, mapping_data, update_model):
        target_class = mapping_data["target"]
        pass

    def _get_transform(self, mapping_data):
        if "function" in mapping_data:
            function_name = mapping_data["function"]
            if hasattr(utils, function_name):
                f = getattr(utils, function_name)
                if not callable(f):
                    raise TransformFunctionError(function_name)
                elif hasattr(f, "hl7_transform_func"):
                    return f
                else:
                    raise TransformFunctionError(function_name)
        else:
            return lambda x: x

    def parse(self, hl7_message, patient, registry_code) -> Tuple[dict, hl7.Message]:
        mapping_map = self.load()
        if not mapping_map:
            raise Exception("cannot parse message as map malformed")

        value_map = {}

        message_model = HL7Message(username="HL7Updater",
                                   event_code=self.event_code,
                                   content=hl7_message,
                                   umrn=get_umrn(hl7_message),
                                   registry_code=registry_code)
        if patient:
            message_model.patient_id = patient.id
        message_model.save()

        for field_moniker, mapping_data in mapping_map.items():
            logger.debug(f"parsing {field_moniker} ...")
            tag = mapping_data.get("tag", "normal")
            logger.debug(f"tag = {tag}")
            handler = self._get_handler(tag)
            logger.debug(f"handler = {handler}")
            update_model = HL7MessageFieldUpdate(hl7_message=message_model,
                                                 hl7_path="unknown",
                                                 data_field=field_moniker)
            try:
                value = handler(hl7_message, field_moniker, mapping_data, update_model)
                logger.debug(f"transformed value = {value}")
                if update_model.failure_reason == "":
                    value_map[field_moniker] = value

            except TransformFunctionError as tfe:
                message = f"Error transforming HL7 field: {tfe}"
                logger.error(message)
                update_model.failure_reason = message

            except KeyError as e:
                message = f"KeyError extracting the field. {e}"
                logger.error(message)
                update_model.failure_reason = message

            except NotFoundError as nf:
                message = f"Not Found Error Extracting field: {nf}"
                logger.error(message)
                update_model.failure_reason = message

            except Exception as ex:
                message = f"Unhandled field error: {ex}"
                logger.error(message)
                update_model.failure_reason = message

            if not update_model.failure_reason:
                update_model.update_status = "Success"

            update_model.save()

        return value_map, message_model

    def _get_hl7_value(self, path, parsed_message):
        # the path notation is understood by python hl7 library
        # see https://python-hl7.readthedocs.io/en/latest/accessors.html
        return parsed_message[path]

    def _apply_transform(self, mapping_data, hl7_value):
        if "tag" not in mapping_data:
            return hl7_value
        tag = mapping_data["tag"]
        if tag == "transform":
            transform = mapping_data["function"]
            if hasattr(utils, transform):
                func = getattr(utils, transform)
            else:
                raise TransformFunctionError(f"Unknown transform function: {transform}")
            if not callable(func):
                raise TransformFunctionError(f"{transform} is not a function")
            if not hasattr(func, "hl7_transform_func"):
                raise TransformFunctionError(f"{transform} is not a HL7 transform")
            try:
                return func(hl7_value)
            except Exception as ex:
                raise TransformFunctionError(f"{transform} inner exception: {ex}")
        elif tag == "mapping":
            mapping = mapping_data["map"]
            return mapping[hl7_value]


class DataRequest(models.Model):
    DATAREQUEST_STATES = ((DataRequestState.REQUESTED, "requested"),
                          (DataRequestState.ERROR, "error"),
                          (DataRequestState.APPLIED, "applied"),
                          (DataRequestState.RECEIVED, "received"))
    requesting_username = models.CharField(max_length=80)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    umrn = models.CharField(max_length=80)
    token = models.CharField(max_length=80, unique=True)
    external_data_json = models.TextField(blank=True, null=True)
    state = models.CharField(max_length=3,
                             choices=DATAREQUEST_STATES,
                             default=DataRequestState.REQUESTED)
    error_message = models.TextField(blank=True, null=True)
    cic_data_json = models.TextField(blank=True, null=True)

    def get_data(self, display=True):
        if self.cic_data_json:
            cic_data = json.loads(self.cic_data_json)

        else:
            cic_data = self.process_data()

        if cic_data is None:
            return None

        if display:
            return self._get_display_data(cic_data)
        else:
            return cic_data

    def process_data(self):
        if self.state != DataRequestState.RECEIVED:
            return None
        if self.external_data_json:
            try:
                external_data = json.loads(self.external_data_json)
            except Exception as ex:
                self.state = DataRequestState.ERROR
                self.error_message = str(ex)
                self.save()
                return None

            datasource = external_data["datasource"]
            data = external_data["data"]
            logger.info(datasource, data)
