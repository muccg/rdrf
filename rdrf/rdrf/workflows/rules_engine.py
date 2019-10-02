from rdrf.models.definition.models import Section
from rdrf.helpers.utils import get_full_path
import logging

logger = logging.getLogger(__name__)


class Tokens:
    EQUALS = "="
    LT = "<"
    LTE = "<="
    GT = ">"
    GTE = ">="
    GET = "get"
    AND = "and"
    OR = "or"
    IN = "in"
    BETWEEN = "between"


class Actions:
    GOTO = "goto"
    WORKFLOW = "workflow"

# should be enough for condition action pairs like:
# [ ["=", ["get", "stoma"], "yes"] , ["goto", "form23"] ] etc
# [ [">", ["get", "BloodPressure"], 130] ,  [ do something ... ]


class RulesEvaluationError(Exception):
    pass


class RulesEvaluator:
    def __init__(self, rules, evaluation_context):
        self.rules = rules
        self.evaluation_context = evaluation_context

    def get_action(self):
        for condition_block, action in self.rules:
            condition = self._eval(condition_block)
            if condition:
                return self._eval_action(action)

    def _eval(self, expr):
        # atoms evaluate themselves
        if not isinstance(expr, type([])):
            return expr
        else:
            head = expr[0]
            if head == Tokens.EQUALS:
                left = expr[1]
                right = expr[2]
                return self._eval(left) == self._eval(right)
            elif head == Tokens.GET:
                cde = expr[1]
                value = self._get_cde_value(cde)
                return value
            elif head == Tokens.AND:
                rest = expr[1:]
                return all(map(self._eval, rest))
            elif head == Tokens.OR:
                rest = expr[1:]
                return any(map(self._eval, rest))
            elif head == Tokens.LT:
                left = expr[1]
                right = expr[2]
                return self._eval(left) < self._eval(right)
            elif head == Tokens.GT:
                left = expr[1]
                right = expr[2]
                return self._eval(left) > self._eval(right)
            elif head == Tokens.GTE:
                left = expr[1]
                right = expr[2]
                return self._eval(left) >= self._eval(right)
            elif head == Tokens.LTE:
                left = expr[1]
                right = expr[2]
                return self._eval(left) <= self._eval(right)
            elif head == Tokens.IN:
                element = self._eval(expr[1])
                a_list = list(map(self._eval, expr[2]))
                result = element in a_list
                return result
            elif head == Tokens.BETWEEN:
                value = self._eval(expr[1])
                low = self._eval(expr[2])
                high = self._eval(expr[3])
                return value >= low and value <= high
            else:
                raise RulesEvaluationError("Unknown head: %s" % head)

    def _get_cde_value(self, field_spec):
        patient_model = self.evaluation_context["patient_model"]
        registry_model = self.evaluation_context["registry_model"]
        context_id = self.evaluation_context.get("context_id", None)
        # faster to load this in
        clinical_data = self.evaluation_context.get("clinical_data", None)

        if "/" in field_spec:
            form_name, section_code, cde_code = field_spec.split("/")
        else:
            form_name, section_code, cde_code = self._get_unique_field(field_spec)

        section_model = Section.objects.get(code=section_code)

        return patient_model.get_form_value(registry_model.code,
                                            form_name,
                                            section_code,
                                            cde_code,
                                            multisection=section_model.allow_multiple,
                                            context_id=context_id,
                                            clinical_data=clinical_data)

    def _get_unique_field(self, cde_code):
        registry_model = self.evaluation_context["registry_model"]
        return get_full_path(registry_model, cde_code)

    def _eval_action(self, action):
        if not isinstance(action, type([])):
            raise RulesEvaluationError("Action should be a list: %s" % action)
        if len(action) == 0:
            raise RulesEvaluationError("Action should be a non-empty list: %s" % action)

        head = action[0]
        if head == Actions.GOTO:
            from django.urls import reverse
            from django.http import HttpResponseRedirect
            url_name = action[1]
            return HttpResponseRedirect(reverse(url_name))
        elif head == Actions.WORKFLOW:
            # set the current workflow somehow ( session ???)
            workflow = action[1]
            logger.info("setting current workflow to %s" % workflow)
        else:
            raise RulesEvaluationError("Unknown action: %s" % head)
