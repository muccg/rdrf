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
    PATIENTS_HEADER = "PID,GIVENNAMES,FAMILYNAME,DOB,ADDRESS,SUBURB,POSTCODE\n"
    PATIENTS_DATA_FILENAME = "patients_data.csv"
    PATIENTS_DATA_HEADER = "PID,QUESTIONNAIRE,CDE,QUESTION,VALUE,COLLECTIONDATE,RESPONSETYPE,FORM\n"
    ADDRESS_FIELD = "Ptaddress1"
    SUBURB_FIELD = "Ptaddress2"
    POSTCODE_FIELD = "Ptaddress3"


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


@cached(maxsize=None)
def is_address_field(cde_code):
    return cde_code in VisDownload.ADDRESS_FIELDS


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


def e(value):
    if "," in value:
        return '"' + value + '"'
    else:
        return value


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
        self.zip_filename = "test.zip"  # self._create_zip_name()
        self.registry = self.custom_action_model.registry
        self.address_map = {}  # pid -> address info from dynamic data

    def _create_zip_name(self):
        registry_code = self.custom_action_model.registry.code
        return VisDownload.ZIP_NAME % registry_code

    def _get_site(self):
        return "prototype"

    def _get_patient_model(self, cd):
        patient_model = Patient.objects.get(id=cd.django_id)
        return patient_model

    def _get_address_field(self, pid, field):
        address_dict = self.address_map.get(pid, {})
        field_value = e(address_dict.get(field, ""))
        return field_value

    def _check_address(self, pid, cde_code, value):
        if cde_code == VisDownload.ADDRESS_FIELD:
            self._update_address(pid, "address", value)
        elif cde_code == VisDownload.SUBURB_FIELD:
            self._update_address(pid, "suburb", value)
        elif cde_code == VisDownload.POSTCODE_FIELD:
            self._update_address(pid, "postcode", value)

    def _update_address(self, pid, field, value):
        if pid in self.address_map:
            m = self.address_map[pid]
        else:
            self.address_map[pid] = {}
            m = self.address_map[pid]

        m[field] = value

    def _emit_patient_line(self, pid, file):
        try:
            patient = Patient.objects.get(id=pid)
            given_names = e(patient.given_names)
            family_name = e(patient.family_name)
            dob = f"{patient.date_of_birth:%d/%m/%Y}"

            address = e(self._get_address_field(pid, "address"))
            suburb = e(self._get_address_field(pid, "suburb"))
            postcode = e(self._get_address_field(pid, "postcode"))

            file.write(f"{pid},{given_names},{family_name},{dob},{address},{suburb},{postcode}\n")

        except Patient.DoesNotExist:
            logger.error(f"vis download: patient {pid} does not exist")
            pass

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
        with open(csv_path, "w") as f:
            f.write(VisDownload.PATIENTS_HEADER)
            for pid in sorted(pids):
                self._emit_patient_line(pid, f)

    def _write_patients_data(self, csv_path, pids):
        logger.debug("writing patients data")

        with open(csv_path, "w") as f:
            f.write(VisDownload.PATIENTS_DATA_HEADER)
            for cd in yield_cds(pids):
                for t in yield_cdes(cd):
                    logger.debug(t)
                    pid = t[0]
                    form_name = t[1]
                    section_code = t[2]
                    qn = t[3]
                    q = t[4]
                    n = e(t[5])
                    v = t[6]
                    self._check_address(pid, q, v)
                    coll = t[7]
                    rt = t[8]
                    line = f"{pid},{qn},{q},{n},{v},{coll},{rt},{form_name}\n"
                    logger.debug(line)
                    f.write(line)
