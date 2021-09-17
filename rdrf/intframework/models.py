import logging
import json
import hl7
from django.db import models
from intframework import utils
from intframework.utils import TransformFunctionError

logger = logging.getLogger(__name__)


class HL7:
    MESSAGE_TYPE_PATH = "MSH.F9.R1.C1"


class DataRequestState:
    REQUESTED = "REC"
    ERROR = "ERR"
    APPLIED = "APP"
    RECEIVED = "REC"


class HL7Mapping(models.Model):
    """
    Facilitate HL7 --> RDRF conversions
    """
    event_code = models.CharField(max_length=20)
    event_map = models.TextField(blank=True, null=True)

    def load(self):
        try:
            return json.loads(self.event_map)
        except ValueError:
            return {}

    def parse(self, hl7_message) -> dict:
        """
        Rather than have lots of models specifying the hl7 translations
        We have a block of JSON
        Something like

        The keys are HL7 event types ( MSH.9.1 ? )

        {"QRY_A19": {"BaseLineClinical/TestSection/CDEName": { "path": "OBX.3.4", "transform": "foobar" },
                    ."<FieldMoniker> : { "path" : <path into hl7 message>,
                                         "transform": "<functionname>" } , }


        """
        mapping_map = self.load()
        value_map = {}

        try:
            msg = hl7.parse(hl7_message)
        except hl7.ParseException as pex:
            logger.error(f"{pex}")
            # what to do?
            return {}

        for field_moniker, mapping_data in mapping_map.items():
            hl7_path = mapping_data["path"]
            logger.info(f"... Extracting {field_moniker} - {hl7_path}")
            try:
                hl7_value = self._get_hl7_value(hl7_path, msg)
                if "transform" in mapping_data.keys():
                    transform_name = mapping_data["transform"]
                    try:
                        rdrf_value = self._apply_transform(transform_name, hl7_value)
                        value_map[field_moniker] = rdrf_value
                    except TransformFunctionError as tfe:
                        logger.error(F"--- Error transforming HL7 field {tfe}")
            except KeyError as e:
                logger.error(f"Error extracting the field. {e}")
                pass
        return value_map

    def _get_event_code(self, parsed_message):
        return self._get_hl7_value(HL7.MESSAGE_TYPE_PATH, parsed_message)

    def _get_hl7_value(self, path, parsed_message):
        # the path notation is understood by python hl7 library
        # see https://python-hl7.readthedocs.io/en/latest/accessors.html
        return parsed_message[path]

    def _apply_transform(self, transform_name, hl7_value):
        if hasattr(utils, transform_name):
            func = getattr(utils, transform_name)
            if not callable(func):
                raise TransformFunctionError(f"{transform_name} is not a function")
            if not hasattr(func, "hl7_transform_function"):
                raise TransformFunctionError(f"{transform_name} is not a HL7 transform")
            try:
                return func(hl7_value)
            except Exception as ex:
                raise TransformFunctionError(f"{transform_name} inner exception: {ex}")
        raise TransformFunctionError(f"Unknown transform function: {transform_name}")


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
