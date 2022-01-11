import pandas as pd
import json
from rdrf.models.definition.models import ClinicalData


class VisualisationDownloadException(Exception):
    pass


def safe(func):
    def wrapper(self, *args, **kwargs):
        try:
            value = func(*args, **kwargs)
            if value is None:
                return pd.NA
            else:
                return value
        except:
            return pd.NA
    return wrapper


class VisualisationDownloader:
    def __init__(self, custom_action_model):
        self.custom_action_model = custom_action_model
        self.column_map = self._generate_column_map()
        self.display_columns = self.column_map.keys()
        self.field_specs = self._get_field_specs()

    def extract(self):
        rows = []

        for cd in ClinicalData.objects.filter(collection="cdes"):
            patient_model = self._get_patient_model(cd)
            if cd.data:
                data = cd.data
                row = [self._get_raw_data(patient_model, field_spec, data) for field_spec in self.field_specs]
                rows.append(row)

        raw = pd.Dataframe(rows, columns=self.display_columns)

        return raw

    def _get_field_specs(self):
        try:
            field_specs = json.loads(self.custom_action_model.data)
        except:
            return []

    def _get_cde(self, form, section, cde, data):
        for form_dict in data["forms"]:
            if form_dict["name"] == form:
                for section_dict in form_dict["sections"]:
                    if section_dict["code"] == section:
                        for cde_dict in section_dict["cdes"]:
                            if cde_dict["code"] == cde:
                                return cde_dict["value"]

    @safe
    def _get_raw_data(self, patient_model, field_spec, data):
        tag = field_spec["tag"]
        if tag == "cde":
            form = field_spec["form"]
            section = field_spec["section"]
            cde = field_spec["cde"]
            return self._get_cde(form, section, cde, data)
        elif tag == "demographics":
            field = field_spec["field"]
            value = getattr(patient_model, field)
            return value
        elif tag == "datarecord":
            field = field_spec["field"]
            value = data[field]
            return value
        else:
            return pd.NA
