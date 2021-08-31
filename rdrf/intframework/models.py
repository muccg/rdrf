import logging
import json
from django.db import models
from intframework import utils
from utils import TransformFunctionError


class DataRequestState:
    REQUESTED = "REC"
    ERROR = "ERR"
    APPLIED = "APP"
    RECEIVED = "REC"


logger = logging.getLogger(__name__)


class HL7Mapping(models.Model):
    event_map = models.TextField(blank=True, null=True)

    def load(self):
        try:
            return json.loads(self.event_map)
        except ValueError:
            return {}

    def parse(self, hl7_message):
        """
        Rather than have lots of models specifying the hl7 translations
        We have a block of JSON
        Something like 

        {"QRY_A19": {"BaseLineClinical/TestSection/CDEName": { "path": "OBX.3.4", "transform": "foobar" },
                    ."<FieldMoniker> : { "path" : <path into hl7 message>,
                                         "transform": "<functionname>" } , }


        """
        event_map = self.load()
        event_code = self._get_event_code(hl7_message)
        value_map = {}
        if event_code in message_map:
            mapping_map = message_map[event_code]
            for field_moniker, mapping_data in mapping_map.items():
                hl7_path = mapping_data["path"]
                hl7_value = self._get_hl7_value(hl7_path, hl7_message)
                transform_name = mapping_data["transform"]
                try:
                    rdrf_value = self._apply_transform(transform_name, hl7_value)
                    value_map[field_moniker] = rdrf_value
                except TransformFunctionError as tfe:
                    logger.error("Error transforming HL7 field")
            return value_map

    def _get_hl7_value(self, path, message):
        return "TODO"

    def _apply_transform(self, transform_name, hl7_value):
        if hasattr(utils, transform_name):
            func = getattr(utils, transform_name)
            if callable(func) and hasattr(func, "hl7_transform_function"):
                rdrf_value = func(hl7_value)


class HL7Message(models.Model):
    code = models.CharField(max_length=80)
    hl7 = models.TextField()

    def build(self, template_data):
        from django.template import Template, Context
        context = Context(template_data)
        return Template(self.hl7).render(context)


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
