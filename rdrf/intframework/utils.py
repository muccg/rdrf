import hl7
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


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
        l = len(messages)
        if l > 1:
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


class MessageSearcher:
    def __init__(self, message: hl7.Message):
        self.message = message
        self.grammar = self._make_grammar()

    def _make_grammar(self):
        import pyparsing as pp
        select = pp.Keyword("select")
        where = pp.Keyword("where")
        component = pp.Combine(pp.Literal("C") + pp.Word(pp.nums))
        component.setParseAction(lambda l: int(l[0][1:]) - 1)
        eq_expression = component + pp.Literal("=") + pp.Word(pp.alphanums)
        select_expression = select + component + where + eq_expression
        return select_expression

    def get_reps(self, field_path, num_components):
        r = 1
        stopped = False
        reps = []
        while not stopped:
            current_values = []
            for c in range(1, num_components+1):
                full_path = f"{field_path}.R{r}.C{c}"
                try:
                    component_value = self.message[full_path]
                    current_values.append(component_value)
                except IndexError:
                    stopped = True
            reps.append(current_values)
            r += 1
        return reps

    def select_matching_items(self, path, num_components, search_expression):
        results = self.grammar.parseString(search_expression)
        select_component_index = results[1]
        where_component_index = results[3]
        value = results[5]
        items = []

        for rep in self.get_reps(path, num_components):
            try:
                if rep[where_component_index] == value:
                    selected_item = rep[select_component_index]
                    items.append(selected_item)
            except IndexError:
                pass

        return items
