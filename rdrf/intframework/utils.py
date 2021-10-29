import hl7
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def get_umrn(message: hl7.Message) -> str:
    try:
        umrn = message["PID.F3"]
        return umrn
    except Exception as ex:
        logger.error(ex)
        return None


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


def patient_not_found(message: hl7.Message) -> bool:
    result = True
    try:
        message.segment("PID")
        result = False
    except KeyError as k:
        logger.error(k)
    return result


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


@transform
def sex(hl7_value):
    return f"{SEX_MAP[hl7_value]}"


def parse_demographics_moniker(moniker: str) -> str:
    field = None
    if "/" in moniker:
        _, field = moniker.split("/")
    return field
