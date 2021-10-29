import hl7
from hl7.client import MLLPClient, read_loose
import io
from datetime import datetime
from django.conf import settings
import logging
from typing import Optional
logger = logging.getLogger(__name__)


class Sep:
    PIPE = "|"
    CARET = "^"
    TILDE = "~"
    BACK_SLASH = "\\"
    AMPERSAND = "&"
    CR = "\r"


class MLLProtocol:
    VT = 11
    FS = 28
    CONTROL_BYTES = [11, 28]


class MessageType:
    PATIENT_QUERY = "QRY^A19^QRY_A19"


def fld(components):
    if type(components) is type(str):
        return hl7.Field("^", components.split("^"))

    return hl7.Field("^", components)


def seg(name, fields):
    return hl7.Segment("|", [name, *fields])


def get_dtm():
    return datetime.now().strftime("%Y%m%d%H%M%S")


class Seg:
    def __init__(self, name):
        self.s = f"{name}"

    def add_field(self, x):
        if not self.s.endswith("|"):
            self.s += "|"
        self.s += x
        if x == "":
            # we allow empty fields
            self.s += "|"


class MessageBuilder:
    def __init__(self, registry_model, user_model):
        # MSH fields
        logger.debug(f"initialising MessageBuilder {registry_model} {user_model}")
        self.seps = r"^~\&"  # noqa: W605
        # sender ( us )
        self.sending_app = settings.APP_ID  # "CIC^HdwaApplication.CIC^L"
        self.sending_facility = settings.SENDING_FACILITY  # "9999^HdwaMedicalFacility.9999^L"
        # receiver ( hub )
        self.receiving_app = settings.HUB_APP_ID  # "ESB^HdwaApplication.ESB^L"
        self.receiving_facility = settings.HUB_FACILITY  # "ESB^HdwaApplication.ESB^L"
        self.dtm = get_dtm()
        self.security = ""  # meant to be empty ..
        self.message_type = MessageType.PATIENT_QUERY
        self.message_model = self._create_message_model(registry_model.code, user_model.username)
        self.message_model.save()  # creates id
        self.message_control_id = self.message_model.message_control_id
        logger.debug(f"message control id = {self.message_control_id}")
        self.query_id = self.message_control_id + ".query"

    def _create_message_model(self, registry_code, username):
        from intframework.models import HL7Message
        message_model = HL7Message()
        message_model.username = username
        message_model.registry_code = registry_code
        message_model.event_code = "QRY_A19"

        return message_model

    def build_qry_a19(self, umrn: str) -> hl7.Message:
        logger.info(f"building qry_a19 for {umrn}")
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
        qrd = self.build_qrd(umrn)
        msg = hl7.parse("\r".join([msh, qrd]))
        self.message_model.content = str(msg)
        self.message_model.save()
        logger.info(f"built message = {msg}")
        return msg

    def build_msh(self) -> str:
        # the hardcoded fields are those which are given in the
        # "Population Notes" in the SPEC as being always the value indicated
        msh = Seg("MSH")
        msh.add_field("^~\&")  # noqa: W605
        msh.add_field(self.sending_app)
        msh.add_field(self.sending_facility)
        msh.add_field(self.receiving_app)
        msh.add_field(self.receiving_facility)
        msh.add_field(self.dtm)
        msh.add_field("")  # security blank
        msh.add_field(MessageType.PATIENT_QUERY)
        msh.add_field(self.message_control_id)
        msh.add_field("D^T")
        msh.add_field(settings.HL7_VERSION)
        msh.add_field("")
        msh.add_field("")  # continuation pointer???
        msh.add_field("AL")
        msh.add_field("NE")
        msh.add_field("AUS")
        msh.add_field("ASCII")
        msh.add_field("en^English^ISO 639-1")
        msh.add_field("")
        msh.add_field("HihHL7v26_3.1^HDWA^^L")
        msh.add_field("")
        msh.add_field("")
        msh.add_field("")
        msh.add_field("")

        logger.debug(f"MSH = {msh.s}")

        return msh.s

    def build_qrd(self, umrn: str) -> str:
        qrd = Seg("QRD")
        qrd.add_field(self.dtm)
        qrd.add_field("R")
        qrd.add_field("I")
        qrd.add_field(self.query_id)
        qrd.add_field("")
        qrd.add_field("")
        qrd.add_field("")
        who_subject_filter = f"{umrn}^^^^^^^^HDWA^^^^MR^0917"  # assigning facility is fixed
        qrd.add_field(who_subject_filter)
        what_subject_filter_field = "DEM^Demographics^HihHL7v26.WhatSubjectFilterCodes^^^1.0.0^^"
        qrd.add_field(what_subject_filter_field)
        return qrd.s


class Client:
    def __init__(self, registry_model, user_model, hub_endpoint, hub_port):
        self.builder = MessageBuilder(registry_model, user_model)
        self.hl7_client = MLLPClient(hub_endpoint,
                                     hub_port)
        self.umrn = None

    def get_data(self, umrn: str) -> dict:
        self.umrn = umrn
        qry_a19_message = self.builder.build_qry_a19(umrn)
        return self.send_message(qry_a19_message)

    def send_message(self, message: hl7.Message) -> dict:
        logger.info(f"hub query for {self.umrn} ..")
        try:
            result_message = hl7.parse(self.hl7_client.send_message(message))
            logger.info(f"hub query success {self.umrn}")
            return {"message": result_message, "status": "success"}
        except hl7.ParseException as pex:
            logger.error(f"hub query fail {self.umrn}: {pex}")
            return {"status": "fail"}
        except Exception as ex:
            logger.error(f"hub query fail {self.umrn}: {ex}")
            return {"status": "fail"}


class MockClient(Client):
    MOCK_MESSAGE = "/data/mock-message.txt"

    def __init__(self, registry_model, user_model, hub_endpoint, hub_port):
        self.builder = MessageBuilder(registry_model, user_model)

    def get_data(self, umrn: str) -> dict:
        qry_a19_message = self.builder.build_qry_a19(umrn)
        return self.send_message(qry_a19_message)

    def send_message(self, message: hl7.Message) -> dict:
        import os
        if os.path.exists(self.MOCK_MESSAGE):
            logger.info("using mock file")
            response_dict = {}
            response_message = self._parse_mock_message_file2(self.MOCK_MESSAGE)
            if response_message is None:
                response_dict["status"] = "fail"
            else:
                response_dict["status"] = "success"
                response_dict["message"] = response_message
        else:
            logger.info("no mock file")
            response_dict = {}

        logger.debug(f"mock response dict = {response_dict}")
        return response_dict

    def _parse_mock_message_file(self, mock_message_file: str) -> Optional[hl7.Message]:

        try:
            binary_data = open(mock_message_file, "rb").read()
            stream = io.BytesIO(binary_data)

            raw_messages = [raw_message for raw_message in read_loose(stream)]
            decoded_messages = [rm.decode("ascii") for rm in raw_messages]

            messages = [hl7.parse(dm) for dm in decoded_messages]
            return messages[1]

        except hl7.ParseException as pex:
            logger.error(f"error parsing mock message: {pex}")
            return None

        except Exception as ex:
            logger.error(f"error loading mock: {ex}")
            return None

    def _parse_mock_message_file2(self, mock_message_file: str) -> Optional[hl7.Message]:
        logger.debug(f"parsing mock file {mock_message_file}")
        # see https://www.hl7.org/documentcenter/public/wg/inm/mllp_transport_specification.PDF
        binary_data = open(mock_message_file, "rb").read()
        data = [b for b in binary_data if b not in MLLProtocol.CONTROL_BYTES]
        ascii_data = "".join(map(chr, data))
        logger.debug(f"ascii data = {ascii_data}")
        try:
            msg = hl7.parse(ascii_data)
            logger.debug("parsed data")
            return msg
        except Exception as ex:
            logger.error("error parsing: %s" % ex)
            return None