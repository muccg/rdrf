import hl7
import json
import logging
from django.conf import settings
from django.db import models
from intframework import utils
from intframework.utils import TransformFunctionError

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


class HL7Mapping(models.Model):
    """
    Facilitate HL7 --> RDRF conversions
    """
    event_code = models.CharField(max_length=20)
    event_map = models.TextField(blank=True, null=True)

    def load(self, event_code):
        try:
            event_map = json.loads(self.event_map)
            logger.debug(f"in load {event_code}")
            logger.debug(f"in load {event_map}")
            mapping_map = event_map[event_code]
            logger.debug(f"in load {mapping_map}")
            return mapping_map
        except ValueError:
            return {}

    def _get_event_code(self, parsed_message):
        return self._get_hl7_value(HL7.MESSAGE_TYPE_PATH, parsed_message)

    def parse(self, hl7_message) -> dict:
        """
        Rather than have lots of models specifying the hl7 translations
        We have a block of JSON
        Something like

        The keys are HL7 event types ( MSH.9.1 ? )

        {"ADR_A19": {
                "BaseLineClinical/TestSection/CDEName": { "path": "OBX.3.4","tag": "transform", "transform": "foobar" },
                "<FieldMoniker> : { "path" : <path into hl7 message>, "tag": "transform", "transform": "<functionname>" } ,
                "<FieldMoniker> : { "path" : <path into hl7 message>, "tag": "mapping", "map": {<dict>} } ,
                }
        }
        """

        event_code = self._get_event_code(hl7_message)
        mapping_map = self.load(event_code)

        value_map = {}

        for field_moniker, mapping_data in mapping_map.items():
            hl7_path = mapping_data["path"]
            logging.info(hl7_path)
            try:
                hl7_value = self._get_hl7_value(hl7_path, hl7_message)
                try:
                    rdrf_value = self._apply_transform(mapping_data, hl7_value)
                    value_map[field_moniker] = rdrf_value
                except TransformFunctionError as tfe:
                    logger.error(F"--- Error transforming HL7 field {tfe}")
                except Exception as ex:
                    logger.error(f"Unhandled field error: {ex}")
            except KeyError as e:
                logger.error(f"KeyError extracting the field. {e}")
                pass
            except Exception as ex:
                logger.error(f"Error: {ex}")
        return value_map

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
