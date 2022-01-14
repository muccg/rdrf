import pandas as pd
import json
import logging
from rdrf.models.definition.models import ClinicalData
from registry.patients.models import Patient

logger = logging.getLogger(__name__)


class VisualisationDownloadException(Exception):
    pass


def safe(func):
    def wrapper(*args, **kwargs):
        logger.debug("in wrapper ...")
        print(args[0])
        print(args[1])
        print(args[2])
        try:
            value = func(*args, **kwargs)
            if value is None:
                return pd.NA
            else:
                logger.debug(f"got value {value}")
                return value
        except Exception as ex:
            logger.debug(f"error getting value: {ex}")
            return pd.NA
    return wrapper


class VisualisationDownloader:
    def __init__(self, custom_action_model):
        self.custom_action_model = custom_action_model
        self.field_specs = self._get_field_specs()
        logger.debug(f"got {len(self.field_specs)} field specs")

    def _get_patient_model(self, cd):
        patient_model = Patient.objects.get(id=cd.django_id)
        logger.debug(f"got {patient_model}")
        return patient_model

    def extract(self):
        rows = []
        num_columns = len(self.field_specs)

        labels = [field_spec["label"] for field_spec in self.field_specs]

        for cd in ClinicalData.objects.filter(collection="cdes"):
            patient_model = self._get_patient_model(cd)
            if cd.data:
                data = cd.data
                try:
                    row = [self._get_raw_data(patient_model, field_spec, data) for field_spec in self.field_specs]
                    logger.debug(row)
                except Exception as ex:
                    logger.error(f"error getting row: {ex}")
                    row = [str(ex)] * num_columns

                rows.append(row)

        raw = pd.DataFrame(rows, columns=labels)
        csv_path = "/data/vd.csv"
        raw.to_csv(csv_path, index=False)

        return raw

    def _get_field_specs(self):
        try:
            data = json.loads(self.custom_action_model.data)
            field_specs = data.get("field_specs", [])
            return field_specs
        except Exception as ex:
            logger.error(f"can't load field specs: {ex}")
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
        logger.debug(f"got tag {tag}")
        if tag == "cde":
            logger.debug("cde field")
            form = field_spec["form"]
            logger.debug(f"form = {form}")
            section = field_spec["section"]
            logger.debug(f"section = {section}")
            cde = field_spec["cde"]
            logger.debug(f"cde = {cde}")
            value = self._get_cde(form, section, cde, data)
            logger.debug(f"value = {value}")
            return value
        elif tag == "demographics":
            logger.debug("demographics field")
            field = field_spec["field"]
            logger.debug(f"field = {field}")
            value = getattr(patient_model, field)
            logger.debug(f"value = {value}")
            return value
        elif tag == "datarecord":
            logger.debug("datarecord field")
            field = field_spec["field"]
            value = data[field]
            logger.debug(f"value = {value}")
            return value
        else:
            logger.debug("unknown field")
            return pd.NA
