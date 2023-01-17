import logging
from django_plotly_dash.models import StatelessApp

logger = logging.getLogger(__name__)


def get_colour_map():
    color_discrete_map = {
        "Blank": "lightgrey",
        "Not at all": "green",
        "A little": "lightgreen",
        "Quite a bit": "darkorange",
        "Very much": "red",
    }
    return color_discrete_map


def get_sevenscale_colour_map():
    # 1 = Very poor and 7 = Excellent
    # used by Health Status and Quality of Life
    return {
        "": "lightgrey",
        "1": "red",
        "2": "lightred",
        "3": "orange",
        "4": "lightblue",
        "5": "blue",
        "6": "lightgreen",
        "7": "green",
    }


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

    if not cde_model.pv_group:
        return None

    d = cde_model.pv_group.as_dict()

    values = set([])
    for value_dict in d["values"]:
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


def create_graphic(vis_config, data, patient, all_patients_data=None):
    # patient is None for all patients graphics
    # contextual single patient components
    # should be supplied with the patient
    # all_patients_data is supplied only to Scale group Comparisons
    # that
    from .components.pcf import PatientsWhoCompletedForms
    from .components.tofc import TypesOfFormCompleted
    from .components.cfc import CombinedFieldComparison
    from .components.cpr import ChangesInPatientResponses
    from .components.sgc import ScaleGroupComparison

    title = vis_config.title
    if vis_config.code == "pcf":
        return PatientsWhoCompletedForms(title, vis_config, data).graphic
    elif vis_config.code == "tofc":
        return TypesOfFormCompleted(title, vis_config, data).graphic
    elif vis_config.code == "cfc":
        return CombinedFieldComparison(title, vis_config, data).graphic
    elif vis_config.code == "cpr":
        return ChangesInPatientResponses(title, vis_config, data).graphic
    elif vis_config.code == "sgc":
        return ScaleGroupComparison(
            title, vis_config, data, patient, all_patients_data
        ).graphic
    else:
        logger.error(f"dashboard error - unknown visualisation {vis_config.code}")
        raise Exception(f"Unknown code: {vis_config.code}")


def get_all_patients_graphics_map(registry, vis_configs):
    from .data import get_data

    data = get_data(registry, None)

    graphics_map = {
        f"tab_{vc.id}": create_graphic(vc, data, None, None) for vc in vis_configs
    }

    return graphics_map


def get_single_patient_graphics_map(registry, vis_configs, patient_id):
    from dashboards.models import VisualisationConfig
    from registry.patients.models import Patient
    from .data import get_data

    logger.debug(f"get single patient graphics for {patient_id}")

    patient = Patient.objects.get(id=patient_id)

    needs_all = needs_all_patients_data(vis_configs)
    data = get_data(registry, patient, needs_all)

    graphics_map = {
        f"tab_{vc.id}": create_graphic(vc, data, patient, None) for vc in vis_configs
    }

    return graphics_map
