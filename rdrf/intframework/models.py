import hl7
import json
import logging
from django.conf import settings
from django.db import models
from intframework import utils
from intframework.utils import TransformFunctionError
from intframework.utils import MessageSearcher

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

    def _handle_search(self, mapping_data):
        path = mapping_data["path"]
        num_components = mapping_data["num_components"]
        search_expression = mapping_data["search_expression"]
        transform = self._get_transform(mapping_data)

        try:
            search_results = self.message_searcher.select_matching_items(path,
                                                                         num_components,
                                                                         search_expression)
            if search_results:
                hl7_value = search_results[0]
                rdrf_value = transform(hl7_value)
                return rdrf_value

        except Exception as ex:
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

    def parse(self, hl7_message, patient, registry_code) -> dict:
        """
        Rather than have lots of models specifying the hl7 translations
        We have a block of JSON
        Something like

        The keys are HL7 event types ( MSH.9.1 ? )

        {
                "BaseLineClinical/TestSection/CDEName": { "path": "OBX.3.4","tag": "transform", "transform": "foobar" },
                "<FieldMoniker> : { "path" : <path into hl7 message>, "tag": "transform", "transform": "<functionname>" } ,
                "<FieldMoniker> : { "path" : <path into hl7 message>, "tag": "mapping", "map": {<dict>} } ,
        }
        """
        self.message_searcher = MessageSearcher(hl7_message)
        mapping_map = self.load()
        if not mapping_map:
            raise Exception("cannot parse message as map malformed")

        value_map = {}

        message_model = HL7Message(username="HL7Updater",
                                   event_code=self.event_code,
                                   content=hl7_message,
                                   registry_code=registry_code)
        if patient:
            message_model.patient_id = patient
        message_model.save()

        for field_moniker, mapping_data in mapping_map.items():
            tag = mapping_data.get("tag", "normal")
            handler_name = f"handle_{tag}"
            if hasattr(self, handler_name):
                handler = getattr(self, handler_name)
                try:

            hl7_path = mapping_data["path"]
            tranform_func = self._get_transform(mapping_data)
            logger.info(hl7_path)
            update_model = HL7MessageFieldUpdate(hl7_message=message_model,
                                                 hl7_path=hl7_path,
                                                 data_field=field_moniker)

            if tag == "normal":
                hl7_value = self._get_hl7_value(hl7_path, hl7_message)

            try:
                hl7_value = self._get_hl7_value(hl7_path, hl7_message)
                update_model.original_value = hl7_value
                try:
                    rdrf_value = self._apply_transform(mapping_data, hl7_value)
                    value_map[field_moniker] = rdrf_value
                except TransformFunctionError as tfe:
                    message = f"Error transforming HL7 field: {tfe}"
                    logger.error(message)
                    update_model.failure_reason = message
                except Exception as ex:
                    message = f"Unhandled field error: {ex}"
                    logger.error(message)
                    update_model.failure_reason = message
            except KeyError as e:
                message = f"KeyError extracting the field. {e}"
                logger.error(message)
                update_model.failure_reason = message
            except Exception as ex:
                message = f"Error: {ex}"
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
