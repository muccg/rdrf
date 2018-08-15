class Tokens:
    EQUALS = "="
    LT = "<"
    LTE = "<="
    GT = ">"
    GTE = ">="
    GET = "get"
    AND = "and"
    OR = "or"
    MEMBER = "member"
    BETWEEN = "between"


# should be enough for condition action pairs like:
# [ ["=", ["get", "stoma"], "yes"] , ["redirect", "form23"] ] etc

# [ [">", ["get", "BloodPressure"], 130] ,  [ do something ... ]


class RulesEvaluationError(Exception):
    pass

class RulesEvaluator:
    def __init__(self, evaluation_context):
        self.evaluation_context = evaluation_context
        self.rules = []

    def load(self, registry_model):
        self.rules = registry_model.metadata["rules"]

    def run(self, stage):
        stage_rules = self.rules[stage]

        for condition_expr, action in stage_rules:
            condition = self._eval(condition_expr) 
            if condition:
                return self._eval_action(action)
            
    def _eval(self, expr):
        if type(expr) is not type([]):
            return expr
        else:
            head = expr[0]
            if head == Tokens.EQUALS:
                left = expr[1]
                right = expr[2]
                return self._eval(left) == self._eval(right)
            elif head == Tokens.GET:
                cde = expr[1]
                return self._get_cde_value(cde)
            elif head == Tokens.AND:
                rest = expr[1:]
                return all(map(self._eval,rest))
            elif head == Tokens.OR:
                rest = expr[1:]
                return any(map(self._eval,rest))
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
            elif head == Tokens.MEMBER:
                element = self._eval(expr[1])
                a_list = map(self._eval,expr[2])
                return element in a_list
            elif head == Tokens.BETWEEN:
                value = self._eval(expr[1])
                low = self._eval(expr[2])
                high = self._eval(expr[3])
                return value >= low and value <= high
            else:
                raise RulesEvaluationError("Unknown head: %s" % head)
