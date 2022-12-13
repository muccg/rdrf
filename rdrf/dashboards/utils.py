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


def get_numeric_values(cde_model):
    if not cde_model.pv_group:
        logger.debug("no pv group returning None")
        return None

    d = cde_model.pv_group.as_dict()
    values = set([])
    for value_dict in d["values"]:
        try:
            i = float(value_dict["code"])
            values.add(i)
        except ValueError:
            return None

    return values


def get_base(cde_code):
    # i.e min value of the range
    from rdrf.models.definition.models import CommonDataElement

    cde_model = CommonDataElement.objects.get(code=cde_code)
    values = get_numeric_values(cde_model)
    if values is None:
        raise ValueError("not a numeric range")

    return min(values)


seq_names = {
    0: "Baseline",
    1: "1st Followup",
    2: "2nd Followup",
    3: "3rd Followup",
    4: "4th Followup",
    5: "5th Followup",
    6: "6th Followup",
    7: "7th Followup",
    8: "8th Followup",
    9: "9th Followup",
    10: "10th Followup",
}


def get_seq_name(seq_num):
    return seq_names.get(seq_num, f"Followup {seq_num}")


def add_seq_name(df):
    df["SEQ_NAME"] = df.apply(lambda row: get_seq_name(row["SEQ"]), axis=1)
    return df


def needs_all_patients_data(vis_configs):
    for vis_config in vis_configs:
        config = vis_config.config
        if "groups" in config:
            for group in config["groups"]:
                if "compare_all" in group:
                    if group["compare_all"]:
                        return True
