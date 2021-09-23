import hl7
from datetime import datetime
from django.conf import settings


class Sep:
    PIPE = "|"
    CARET = "^"
    TILDE = "~"
    BACK_SLASH = "\\"
    AMPERSAND = "&"
    CR = "\r"


class MessageType:
    PATIENT_QUERY = "QRY^A19^QRY_A19"


def DTM():
    return datetime.now().strftime("%Y%m%d%H%M%S")


class MessageBuilder:
    def __init__(self, registry_model, user_model):
        # MSH fields
        from django.conf import setings
        self.seps = "^~\&"
        self.sending_app = settings.HL7_HUB_SENDING_APP  # "CIC^HdwaApplication.CIC^L"
        self.sending_facility = settings.HL7_HUB_SENDING_FACILITY  # "9999^HdwaMedicalFacility.9999^L"
        self.receiving_app = settings.HL7_HUB_RECEIVING_APP  # "ESB^HdwaApplication.ESB^L"
        self.receiving_facility = settings.HL7_HUB_RECEIVING_FACILITY  # "ESB^HdwaApplication.ESB^L"
        self.dtm = DTM()
        self.security = ""  # meant to be empty ..
        self.message_type = MessageType.PATIENT_QUERY
        self.message_model = self._create_message_model(registry_model.code, user_model.username)
        self.message_model.save()  # creates id
        self.message_control_id = self.message_model.message_control_id

    def _create_message_model(self, username, registry_code):
        from intframework.models import HL7Message
        message_model = HL7Message()
        message_model.username = username
        message_model.registry_code = registry_code
        return message_model

    def build_qry_a19(self, umrn: str) -> hl7.message:
        # from "HIH12-5A  WA Health - HL7 Specification v4.7.pdf" [SPEC] p126
        # MSH|^~\&|MOSIAQ^HdwaApplication.MOSIAQ^L|0106^HdwaMedicalFacility.0106^L|ESB^HdwaApplication.ESB^L|0917^HdwaMedicalFacility.0917^L|20140415092747||QRY^A19^QRY_A19|MOSIAQ.0106.13391835|D^T|2.6|||AL|NE|AUS|ASCII|en^English^ISO 639-1||HihHL7v26_4.1^HDWA^^L
        # QRD|20140415092735|R|I|MOSIAQ.0106.5994358||||E9326541^^^^^^^^HDWA^^^^MR^0917|DEM^Demographics^HihHL7v26.WhatSubjectFilterCodes^^^1.0.0^^
        # says QRF is reserved for future use?
        # web example:
        # one example page I could find http://ringholm.com/docs/00300_en.htm
        # msh = "MSH|^~\&|KIS||CommServer||200811111017||QRY^A19||P|2.2|"
        # commented with comment(<page reference in SPEC>)
        # date time format (DTM)  YYYYMMDDHHMMSS[.S[S[S[S]]]]
        msh = self.build_msh()
        qrd = self.build_qrd()
        msg = hl7.parse("\r".join([msh, qrd]))
        return msg

    def build_msh(self):
        # MSH|^~\&|CIC^HdwaApplication.CIC^L|9999^HdwaMedicalFacility.9999^L|ESB^HdwaApplication.ESB^L|0917^HdwaMedicalFacility.0917^L|20140415092747||QRY^A19^QRY_A19|MOSIAQ.0106.13391835|D^T            |2.6|||AL|NE|AUS|ASCII|en^English^ISO 639-1||HihHL7v26_4.1^HDWA^^L
        #                      seg seps(285)  sending app(285)     sending facility(285)          receiving app(286)         receiving facility(287)        DTM  of message|S| msg type(289) | msg control id(290)| proc id(290)| vers
        # NB.  S ( security ) is empty reserved for future use
        return "MSH"

    def build_qrd(self):
        # qrd = f"QRD | {timestamp() | R | I |
        #qrd = "QRD|200811111016|R|I|Q1004|||1^RD|10000437363|DEM|||"
        return "QRD"


class Client:
    def __init__(self, registry_model, user_model, hub_endpoint, hub_port):
        self.hub_endpoint = hub_endpoint
        self.hub_port = hub_port
        self.builder = MessageBuilder(registry_model, user_model)

    def get_data(self, umrn: str) -> dict:
        qry_a19_message = self.builder.build_qry_a19(umrn)
        response_dict = self.send_message(qry_a19_message)
        return response_dict

    def send_message(self, message: hl7.Message) -> dict:
        return {}
