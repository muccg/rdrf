import hl7
import logging

logger = logging.getLogger(__name__)


def inspect_msg(message, seg):
    f = 1
    c = 0
    while f <= 20:
        while c <= 20:
            try:
                if c == 0:
                    expr = f"{seg}.{f}"
                else:
                    expr = f"{seg}.{f}.{c}"
                value = message[expr]
                logger.debug(f"{expr}={value}")
            except Exception as ex:
                logger.error(f"{expr} error: {ex}")

            c += 1
        f += 1


def t(msg, seg, i, j=None):
    if j is None:
        key = f"{seg}.{i}"
    else:
        key = f"{seg}.{i}.{j}"
    try:
        if j is not None:
            logger.debug(f"{key} = " + str(msg[f"{seg}.{i}.{j}"]))
        else:
            logger.debug(f"{key} = " + str(msg[f"{seg}.{i}"]))
    except Exception as ex:
        pass


def get_event_code(message: hl7.Message) -> str:
    logger.debug("event code ")
    try:
        ec = message["MSH.F9.R1.C3"]  # ADR_A19  message structure
        logger.debug("event code = %s" % ec)
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


@ transform
def identity(hl7_value):
    return hl7_value


@ transform
def date(hl7_value):
    return f"{hl7_value[:8]}"
