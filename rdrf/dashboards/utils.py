import logging

logger = logging.getLogger(__name__)


def get_colour_map():
    color_discrete_map = {
        "Not at all": "lightgreen",
        "A little": "orange",
        "Quite a bit": "darkorange",
        "Very much": "red",
    }
    return color_discrete_map


def get_range(cde_model):
    """
    Return the numeric range
    of a range cde
    e.g.
    if the allowed values are
    1
    2
    3
    the range is 3 - 1 = 2
    """

    logger.debug(f"getting range for {cde_model.code}")

    if not cde_model.pv_group:
        logger.debug("no pv group returning None")
        return None

    d = cde_model.pv_group.as_dict()

    values = set([])
    for value_dict in d["values"]:
        print(f"checking {value_dict}")
        try:
            # The numeric values are stored with the code key
            i = float(value_dict["code"])
            values.add(i)
        except ValueError:
            return None

    max_value = max(values)
    min_value = min(values)
    return max_value - min_value
