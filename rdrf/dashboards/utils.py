import logging

logger = logging.getLogger(__name__)


def get_colour_map():
    color_discrete_map = {
        "Missing": "lightgrey",
        "Not at all": "green",
        "A little": "yellow",
        "Quite a bit": "orange",
        "Very much": "red",
    }
    return color_discrete_map


def get_sevenscale_colour_map():
    # 1 = Very poor and 7 = Excellent
    # used by Health Status and Quality of Life
    return {
        "": "lightgrey",
        "1": "darkred",
        "2": "orangered",
        "3": "orange",
        "4": "gold",
        "5": "yellow",
        "6": "greenyellow",
        "7": "limegreen",
        "Missing": "lightgrey",
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
    def colldate(row):
        if "COLLECTIONDATE" in row:
            return f" ({row['COLLECTIONDATE']})"
        else:
            return ""

    df["SEQ_NAME"] = df.apply(
        lambda row: get_seq_name(row["SEQ"]) + colldate(row),
        axis=1,
    )
    return df


def needs_all_patients_data(vis_configs):
    for vis_config in vis_configs:
        config = vis_config.config
        if "groups" in config:
            for group in config["groups"]:
                if "compare_all" in group:
                    if group["compare_all"]:
                        return True


def handle_value_error(func):
    def wrapper(vis_config, data, patient, all_patients_data=None, static_followups={}):
        try:
            return func(vis_config, data, patient, all_patients_data, static_followups)
        except ValueError as ve:
            logger.error(f"Error in create graphic {vis_config.code}: {ve}")
            return "Not enough data"

    return wrapper


@handle_value_error
def create_graphic(
    vis_config, data, patient, all_patients_data=None, static_followups={}
):
    # patient is None for all patients graphics
    # contextual single patient components
    # should be supplied with the patient
    # all_patients_data is supplied only to Scale group Comparisons
    # that

    from .components.proms_stats import PatientsWhoCompletedForms
    from .components.cfc import CombinedFieldComparison
    from .components.cpr import ChangesInPatientResponses
    from .components.sgc import ScaleGroupComparison
    from .components.tl import TrafficLights

    title = vis_config.title
    if vis_config.code == "proms_stats":
        from dash import html

        pcf_graphic = PatientsWhoCompletedForms(
            "Patients Who Completed Forms", vis_config, data
        ).graphic
        return html.Div([pcf_graphic], "proms_stats")
    elif vis_config.code == "cfc":
        return CombinedFieldComparison(title, vis_config, data).graphic
    elif vis_config.code == "cpr":
        return ChangesInPatientResponses(title, vis_config, data).graphic
    elif vis_config.code == "sgc":
        return ScaleGroupComparison(
            title, vis_config, data, patient, all_patients_data
        ).graphic
    elif vis_config.code == "tl":
        return TrafficLights(
            title, vis_config, data, patient, all_patients_data, static_followups
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
    from registry.patients.models import Patient
    from dashboards.models import VisualisationBaseDataConfig
    from .data import get_data
    from dash import html

    no_data = True

    patient = Patient.objects.get(id=patient_id)

    needs_all = needs_all_patients_data(vis_configs)

    base_config_model = VisualisationBaseDataConfig.objects.get(registry=registry)
    base_config = base_config_model.config
    static_followups = {}
    static_followup_forms = base_config.get("followup_forms", [])
    if static_followup_forms:
        static_followups["followups"] = static_followup_forms
        static_followups["baseline"] = base_config.get("baseline_form", None)

    try:
        data = get_data(registry, patient, needs_all)
        if data is not None:
            no_data = False
    except Exception as ex:
        logger.error(f"Error getting patient data for {patient_id}: {ex}")
        return {f"tab_{vc.id}": html.H3("An error occurred") for vc in vis_configs}

    if no_data:
        return {f"tab_{vc.id}": html.H3("No data") for vc in vis_configs}

    graphics_map = {
        f"tab_{vc.id}": create_graphic(vc, data, patient, None, static_followups)
        for vc in vis_configs
    }

    return graphics_map


def dump(name, data):
    name = name.replace("/", "")
    filename = f"/data/{name}.csv"
    data.to_csv(filename)


def get_aus_date(row):
    try:
        d = row["COLLECTIONDATE"].date()
        aus_date = f"{d.day}-{d.month}-{d.year}"
        if "nan" in aus_date:
            return ""
        return f" ({aus_date})"
    except KeyError:
        return ""
    except ValueError:
        return ""


def assign_seq_names(df, func=None):
    if func is None:
        df["SEQ_NAME"] = df.apply(
            lambda row: get_seq_name(row["SEQ"]) + get_aus_date(row), axis=1
        )
    else:
        df["SEQ_NAME"] = df.apply(
            lambda row: func(row["SEQ"], row["FORM"]) + get_aus_date(row), axis=1
        )

    return df


class DataFrameError(Exception):
    pass


def sanity_check(where, df):
    for index, row in df.iterrows():
        seq = row["SEQ"]
        form_type = row["TYPE"]
        form = row["FORM"]
        if form_type == "baseline" and seq > 0:
            raise DataFrameError(
                f"{where} baseline should have seq 0: {form} has seq = {seq}"
            )
        if form_type == "followup" and seq == 0:
            raise DataFrameError(
                f"{where} followup should have seq > 0: {form} has seq = 0"
            )
