from functools import lru_cache as cached
import json
import logging
import pandas as pd
from datetime import datetime
from rdrf.models.definition.models import ClinicalData
from rdrf.models.definition.models import CommonDataElement
from rdrf.models.definition.models import RDRFContext
from registry.patients.models import Patient
from rdrf.helpers.utils import generate_token
from django.contrib.sites.shortcuts import get_current_site
from django.db.models import Q


logger = logging.getLogger(__name__)


class VisDownload:
    ZIP_NAME = "visualisation_download-%s.zip"
    PATIENTS_FILENAME = "patients.csv"
    PATIENTS_HEADER = "PID,GIVENNAMES,FAMILYNAME,DOB,ADDRESS,SUBURB,POSTCODE,WORKINGGROUP\n"
    PATIENTS_DATA_FILENAME = "patients_data.csv"
    PATIENTS_DATA_HEADER = "PID,QUESTIONNAIRE,CDE,QUESTION,VALUE,COLLECTIONDATE,RESPONSETYPE,FORM\n"


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
    dv = cde_model.get_display_value(raw_value)
    if type(dv) is list:
        return ";".join(dv)
    else:
        return dv


@cached(maxsize=None)
def get_questionnaire_number(code):
    try:
        qn, q = code.split("_Q")
        return qn, q
    except:
        return "", code


def retrieve(cd, cde):
    for f in cd.data["forms"]:
        for s in f["sections"]:
            if not s["allow_multiple"]:
                for c in s["cdes"]:
                    if c["code"] == cde:
                        return c["value"]


def aus_date_string(us_date_string):
    if us_date_string:
        try:
            d = datetime.strptime(us_date_string, "%Y-%m-%d")
            return f"{d:%d/%m/%Y}"
        except:
            pass
    return ""


def get_collection_date(cd):
    raw_value = retrieve(cd, "COLLECTIONDATE")
    return aus_date_string(raw_value)


def get_response_type(cd):
    # are we in a followup or baseline record
    context_id = cd.context_id
    context_model = RDRFContext.objects.get(id=context_id)
    if context_model.context_form_group:
        cfg = context_model.context_form_group
        if cfg.context_type == "M":
            return "Multiple"
    return "OnceOff"


def yield_cds(pids):
    for cd in ClinicalData.objects.filter(collection="cdes",
                                          django_model="Patient",
                                          django_id__in=pids):
        if cd.data and "forms" in cd.data:
            yield cd


def yield_cdes(cd):
    # this will only work if there is one form with collection date
    pid = cd.django_id
    collection_date = get_collection_date(cd)
    response_type = get_response_type(cd)

    data = cd.data
    for f in data["forms"]:
        form_name = f["name"]
        for s in f["sections"]:
            section_code = s["code"]
            if not s["allow_multiple"]:
                for c in s["cdes"]:
                    code = c["code"]
                    questionnaire, question = get_questionnaire_number(code)
                    cde = get_cde_model(code)
                    name = cde.name
                    value = c["value"]
                    logger.debug(f"{code} = {value}")
                    try:
                        display_value = get_display_value(code, value)
                    except Exception as ex:
                        logger.error(f"error {code}: {ex}")
                        display_value = "ERROR"
                    yield (pid,
                           form_name,
                           section_code,
                           questionnaire,
                           question,
                           name,
                           display_value,
                           collection_date,
                           response_type)


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
        self.zip_filename = "test.zip"  # self._create_zip_name()
        self.registry = self.custom_action_model.registry

    def _create_zip_name(self):
        registry_code = self.custom_action_model.registry.code
        return VisDownload.ZIP_NAME % registry_code

    def _get_site(self):
        return "prototype"

    def _get_patient_model(self, cd):
        patient_model = Patient.objects.get(id=cd.django_id)
        return patient_model

    @property
    def task_result(self):
        import os.path
        from django.conf import settings
        task_dir = settings.TASK_FILE_DIRECTORY
        filename = generate_token()
        filepath = os.path.join(task_dir, filename)
        patients_csv_filepath = "/data/patients.csv"
        patients_data_csv_filepath = "/data/patients_data.csv"
        self.extract_long(patients_csv_filepath,
                          patients_data_csv_filepath)
        result = {"filepath": filepath,
                  "content_type": "text/csv",
                  "username": self.user.username,
                  "user_id": self.user.id,
                  "filename": self.zipfile_name,
                  }
        return result

    def _get_patients_in_users_groups(self):
        logger.debug("in get patients")
        in_wgs = Q(working_groups__in=self.user.working_groups.all(), active=True)
        in_reg = Q(rdrf_registry__in=[self.registry])
        query = in_wgs & in_reg
        return Patient.objects.filter(query)

    def extract_long(self, patients_csv_filepath, patients_data_csv_filepath):
        logger.debug("in extract_long")
        patients = self._get_patients_in_users_groups()
        logger.debug(f"{patients}")
        pids = [id for id in patients.values_list('id', flat=True)]
        logger.debug(f"patients in users groups: {pids}")
        self._write_patients(patients_csv_filepath, pids)
        self._write_patients_data(patients_data_csv_filepath, pids)

    def _write_patients(self, csv_path, pids):
        pass

    def _write_patients_data(self, csv_path, pids):
        logger.debug("writing patients data")

        def e(value):
            # enquote
            if "," in value:
                return '"' + value + '"'
            else:
                return value
        with open(csv_path, "w") as f:
            f.write(VisDownload.PATIENTS_DATA_HEADER)
            for cd in yield_cds(pids):
                for t in yield_cdes(cd):
                    logger.debug(t)
                    p = t[0]
                    form_name = t[1]
                    section_code = t[2]
                    qn = t[3]
                    q = t[4]
                    n = e(t[5])
                    v = t[6]
                    coll = t[7]
                    rt = t[8]
                    line = f"{p},{qn},{q},{n},{v},{coll},{rt},{form_name}\n"
                    logger.debug(line)
                    f.write(line)

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

    @ safe
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
