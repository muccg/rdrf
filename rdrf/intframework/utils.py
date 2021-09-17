class TransformFunctionError(Exception):
    pass


def transform(func):
    """
    Decorator to m transform funcs
    """
    func.hl7_transform_func = True
    return func


@transform
def identity(hl7_value):
    return hl7_value


@transform
def date(hl7_value):
    return f"{hl7_value[:8]}"
