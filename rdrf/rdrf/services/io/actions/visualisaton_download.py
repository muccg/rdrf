from functools import lru_cache as cached
import json
import logging
import pandas as pd
from rdrf.models.definition.models import ClinicalData
from rdrf.models.definition.models import CommonDataElement
from registry.patients.models import Patient

logger = logging.getLogger(__name__)


@cached(maxsize=None)
def get_cde_model(cde_code) -> CommonDataElement:
    return CommonDataElement.objects.get(code=cde_code)


@cached(maxsize=None)
def get_display_value(cde_code, raw_value):
    try:
        cde_model = get_cde_model(cde_code)
    except CommonDataElement.DoesNotExist:
        logger.error(f"{cde_code} does not exist")
        return "NOCDE"
    return cde_model.get_display_value(raw_value)


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
    def __init__(self, user, custom_action_model):
        self.user = user
        self.custom_action_model = custom_action_model
        self.field_specs = self._get_field_specs()

    def _get_patient_model(self, cd):
        patient_model = Patient.objects.get(id=cd.django_id)
        return patient_model

    @property
    def task_result(self):
        import os.path
        from rdrf.helpers.utils import generate_token
        from django.conf import settings
        task_dir = settings.TASK_FILE_DIRECTORY
        filename = generate_token()
        filepath = os.path.join(task_dir, filename)
        with open(filepath, "w") as f:
            self.extract(f)
        result = {"filepath": filepath,
                  "content_type": "text/csv",
                  "username": self.user.username,
                  "user_id": self.user.id,
                  "filename": "visualisation_download.csv",
                  }
        return result

    def extract(self, csv_path):

        rows = []
        num_columns = len(self.field_specs)

        labels = [field_spec["label"] for field_spec in self.field_specs]

        for cd in ClinicalData.objects.filter(collection="cdes"):
            patient_model = self._get_patient_model(cd)
            if cd.data:
                data = cd.data
                try:
                    row = [self._get_data(patient_model, field_spec, data) for field_spec in self.field_specs]
                except Exception as ex:
                    logger.error(f"error getting row: {ex}")
                    row = [str(ex)] * num_columns

                rows.append(row)

        raw = pd.DataFrame(rows, columns=labels)

        raw.to_csv(csv_path, index=False)
        logger.debug(f"saved to csv file to path {csv_path}")

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
                                return get_display_value(cde, cde_dict["value"])

        return "NODATA"

    @safe
    def _get_data(self, patient_model, field_spec, data):
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
            value = get_display_value(cde, self._get_cde(form, section, cde, data))
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
