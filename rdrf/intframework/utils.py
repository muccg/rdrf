import hl7
import logging
from datetime import datetime
from typing import Optional, Tuple
import re

logger = logging.getLogger(__name__)

field_pattern = re.compile("^(.*\.F\d+).*$")


def get_segment_field(path):
    # from PID.F13.R1.C3  we want
    # PID.F13 returned as a pair : "PID", "F13"
    logger.debug(f"getting field from path {path}")
    m = field_pattern.search(path)
    if m:
        logger.debug("field pattern found a match")
        field_path = m.group(1)
        segment, field = field_path.split(".")
        logger.debug(f"segment = {segment} field = {field}")
        return segment, field
    logger.debug("field pattern did not match")
    return None


def field_empty(message: hl7.Message, path: str) -> bool:
    # path is something like PID.F13
    segment, field_expr = get_segment_field(path)
    field_num = int(field_expr.replace("F", ""))
    hl7_field = message[segment][0][field_num]  # this is an object
    field_value = f"{hl7_field}"
    logger.debug(f"{segment}.{field_expr} = <{field_value}>")
    if not field_value:
        logger.debug(f"{segment}.F{field_num} is empty!: {field_value}")
        return True
    else:
        logger.debug(f"{segment}.F{field_num} is not empty: <{field_value}>")
        return False


def get_umrn(message: hl7.Message) -> str:
    try:
        umrn = message["PID.F3"]
        return umrn
    except Exception as ex:
        logger.error(ex)
        return ""


def get_event_code(message: hl7.Message) -> str:
    logger.info("get event code ")
    try:
        ec = message["MSH.F9.R1.C3"]  # ADR_A19  message structure
        if not len(ec):
            raise Exception
        logger.info("event code = %s" % ec)
        return ec
    except Exception as ex:
        logger.error(ex)
        try:
            ec = f'{message["MSH.F9.R1.C1"]}_{message["MSH.F9.R1.C2"]}'  # message code and trigger event
            logger.info("event code = %s" % ec)
            return ec
        except Exception as ex:
            logger.error(ex)
            return "error"


def patient_found(message: hl7.Message) -> bool:
    """
    patient found == message contains PID segment
    """
    try:
        message["PID"]
        return True
    except Exception:
        pass
    return False


def patient_subscribed(message: hl7.Message) -> bool:
    """
    Look for AA status code of MSA Accept Acknowledgement Code
    """
    try:
        return message["MSA.1"] == "AA"
    except Exception:
        pass
    return False


class TransformFunctionError(Exception):
    pass


class FieldSource:
    LOCAL = "local"
    EXTERNAL = "external"


def get_field_source(cde_code):
    from intframework.models import HL7Mapping

    key = f"/{cde_code}"
    for hl7_mapping in HL7Mapping.objects.all():
        mapping_dict = hl7_mapping.load()
        for field_moniker in mapping_dict:
            if field_moniker.endswith(key):
                return FieldSource.EXTERNAL
    return FieldSource.LOCAL


def transform(func):
    """
    Decorator to mark a function as a transform
    """
    func.hl7_transform_func = True
    return func


@transform
def identity(hl7_value):
    return hl7_value


@transform
def date(hl7_value):
    if hl7_value == '""':
        return None
    if hl7_value == "":
        return None
    return datetime.strptime(hl7_value[:8], "%Y%m%d")


"""
HL7 values
Value	Description
F	    Female
M	    Male
O	    Other
U	    Unknown
A	    Ambiguous
N	    Not applicable
"""
SEX_MAP = {"M": 1, "F": 2, "U": 3, "O": 3, "A": 3, "N": 3}


CODE_TABLES = {"place_of_birth":
               {'0901': 'New South Wales',
                '0902': 'Victoria',
                '0903': 'Queensland',
                '0904': 'South Australia',
                '0905': 'Western Australia',
                '0906': 'Tasmania',
                '0907': 'Northern Territory',
                '0908': 'Aust Cap Territory',
                '0909': 'Christmas Cocos Island',
                '1101': 'Australia',
                '1102': 'Norfolk Island',
                '1199': 'Australian External Territories, nec',
                '1201': 'New Zealand', '1301': 'New Caledonia',
                '1302': 'Papua New Guinea',
                '1303': 'Solomon Islands',
                '1304': 'Vanuatu',
                '1401': 'Guam',
                '1402': 'Kiribati',
                '1403': 'Marshall Islands',
                '1404': 'Micronesia, Federated States of',
                '1405': 'Nauru',
                '1406': 'Northern Mariana Islands',
                '1407': 'Palau',
                '1501': 'Cook Islands',
                '1502': 'Fiji',
                '1503': 'French Polynesia',
                '1504': 'Niue',
                '1505': 'Samoa',
                '1506': 'Samoa, American'}}


@ transform
def sex(hl7_value):
    return f"{SEX_MAP[hl7_value]}"


def parse_demographics_moniker(moniker: str) -> Optional[str]:
    field = None
    if "/" in moniker:
        _, field = moniker.split("/")
    return field


def parse_cde_moniker(moniker: str) -> Optional[Tuple[str, str, str]]:
    # get form_name, section_code, cde_code
    parts = moniker.split("/")
    assert len(parts) == 3
    assert parts[0] != "Demographics"
    pass


def load_message(message_file: str):
    # used for interactive testing
    import io
    import hl7
    from hl7.client import read_loose
    try:
        binary_data = open(message_file, "rb").read()
        stream = io.BytesIO(binary_data)
        raw_messages = [raw_message for raw_message in read_loose(stream)]
        decoded_messages = [rm.decode("ascii") for rm in raw_messages]
        messages = [hl7.parse(dm) for dm in decoded_messages]
        num_messages = len(messages)
        if num_messages > 1:
            return messages[1]
        else:
            return messages[0]
    except hl7.ParseException as pex:
        print(pex)
        return None
    except Exception as ex:
        print(ex)
        return None


class SearchExpressionError(Exception):
    pass


class NotFoundError(Exception):
    pass


class FieldEmpty(Exception):
    pass


class MessageSearcher:
    def __init__(self, field_mapping):
        self.field_mapping = field_mapping
        self.prefix = self.field_mapping["path"]
        self.select = self.field_mapping["select"]
        self.where = self.field_mapping["where"]
        self.num_components = self.field_mapping["num_components"]
        self.repeat = 1

    def get_component(self, repeat, component, message):
        full_key = f"{self.prefix}.R{repeat}.{component}"
        return message[full_key]

    def get_value(self, message: hl7.Message):
        if field_empty(message, self.prefix):
            logger.debug("path is empty so raising FieldEmpty - won't update")
            raise FieldEmpty(self.prefix)

        # otherwise we try to extract the component specified
        r = 1
        stopped = False
        while not stopped:
            try:
                where_actual = self.get_where_dict(r, message)
                if where_actual == self.where:
                    value = self.get_component(r, self.select, message)
                    return value
                r += 1
            except IndexError:
                stopped = True

        raise NotFoundError(str(self))

    def get_where_dict(self, repeat, message):
        return {k: self.get_component(repeat, k, message) for k in self.where}

    def __str__(self):
        w = ""
        for k in sorted(self.where):
            w += f" {k}={self.where[k]}"
        return f"SELECT {self.select} WHERE{w}"


def parse_message_file(registry, user, patient, event_code, message_file):
    from intframework.models import HL7Mapping
    from intframework.hub import MockClient
    model = HL7Mapping.objects.all().get(event_code=event_code)
    mock_client = MockClient(registry, user, None, None)
    parsed_message = mock_client._parse_mock_message_file(message_file)
    parse_dict = model.parse(parsed_message, patient, registry.code)
    return parse_dict


def hl7_field(event_code, field_spec, default_value):
    from intframework.models import HL7MessageConfig
    try:
        message_config = HL7MessageConfig.objects.get(event_code=event_code)
        return message_config.config.get(field_spec, default_value)
    except HL7MessageConfig.DoesNotExist:
        return default_value


def parse_message(message_file):
    """
    A helper for interactive debugging
    """
    from rdrf.models.definition.models import Registry
    from registry.groups.models import CustomUser
    from intframework.hub import MockClient
    registry = Registry.objects.get()
    user = CustomUser.objects.get(username="admin")
    mock_client = MockClient(registry, user, None, None)
    return mock_client._parse_mock_message_file(message_file)


def empty_value_for_field(field):
    if "date_" in field:
        return None
    return ""
