import hl7
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def get_event_code(message: hl7.Message) -> str:
    logger.info("get event code ")
    try:
        ec = message["MSH.F9.R1.C3"]  # ADR_A19  message structure
        logger.info("event code = %s" % ec)
        return ec
    except Exception as ex:
        logger.error(ex)
        return "error"


class TransformFunctionError(Exception):
    pass


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
    # this assumes that the dattime string will be in the form yyyymmddHHMMSS
    datetime_object = datetime.strptime(hl7_value, '%Y%m%d%H%M%S')
    return datetime_object


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
