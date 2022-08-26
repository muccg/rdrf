from functools import lru_cache as cached
import logging
import shutil
from datetime import datetime
from rdrf.models.definition.models import ClinicalData
from rdrf.models.definition.models import CommonDataElement
from rdrf.models.definition.models import RDRFContext
from registry.patients.models import Patient
from rdrf.helpers.utils import generate_token
from django.db.models import Q
from zipfile import ZipFile


logger = logging.getLogger(__name__)


class ResearchDownload:
    ZIP_NAME = "CICResearchDownload%s%s.zip"
    PATIENTS_DATA_FILENAME = "patients_data.csv"
    PATIENTS_DATA_HEADER = "PID,QUESTIONNAIRE,CDE,QUESTION,VALUE,COLLECTIONDATE,RESPONSETYPE,FORM,INDEX\n"


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
    if cde_model.datatype == "date":
        return aus_date_string(raw_value)
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
    except Exception:
        return "", code


@cached(maxsize=None)
def is_address_field(cde_code):
    return cde_code in ResearchDownload.ADDRESS_FIELDS


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
        except Exception:
            pass
    return ""


def aus_date(dt: datetime) -> str:
    if dt:
        return f"{dt:%d/%m/%Y}"
    else:
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


class Downloader:
    def __init__(self, user, custom_action_model):
        self.user = user
        self.datestamp = f"{datetime.now().date():%d%m%Y}"
        self.custom_action_model = custom_action_model
        self.registry = self.custom_action_model.registry
        self.all_cdes = False
        self.patterns = []
        self.fields = []
        self.deident_map = {}
        self.dob_map = {}
        self.sex_map = {}
        self._parse_fields(custom_action_model)

    def _get_config(self, data):
        return data.get("config", {})

    def _get_deident(self, pid):
        deident = self._get_field(pid, "deident")
        return (pid,
                "",
                "",
                "deident",
                "",
                "",
                "Deidentified Token",
                deident,
                "",
                "",
                1)  # index column

    def _get_dob(self, pid):
        dob = self._get_field(pid, "dob")
        return (pid,
                "Demographics",
                "",
                "DOB",
                "",
                "",
                "Date of Birth",
                dob,
                "",
                "",
                1)  # index column

    def _get_sex(self, pid):
        sex = self._get_field(pid, "sex")
        return (pid,
                "Demographics",
                "",
                "Sex",
                "",
                "",
                "Sex",
                sex,
                "",
                "",
                1)  # index column

    def _parse_fields(self, custom_action_model):
        import json
        data = json.loads(custom_action_model.data)
        self.patterns = []
        self.fields = []
        fields = data["fields"]
        if fields == "all":
            self.all_cdes = True
            return

        self.config = self._get_config(data)
        self.delimiter = self.config.get("delimiter", "|")
        for spec in fields:
            if spec.endswith("*"):
                self.patterns.append(spec[:-1])
            else:
                self.fields.append(spec)
        self.fields = set(self.fields)

    @property
    def zip_name(self):
        user_groups = "_".join(sorted([wg.name.upper() for wg in self.user.working_groups.all()]))
        registry_code = self.registry.code
        name = f"CICResearchDownload_{registry_code}_{user_groups}_{self.datestamp}.zip"
        return name

    def _get_site(self):
        return "prototype"

    @property
    def task_result(self):
        import os.path
        from django.conf import settings
        task_subfolder_name = generate_token()
        task_dir = os.path.join(settings.TASK_FILE_DIRECTORY, task_subfolder_name)
        zip_filename = os.path.join(settings.TASK_FILE_DIRECTORY, generate_token())
        os.makedirs(task_dir)
        patients_data_csv_filepath = os.path.join(task_dir, "patients_data.csv")
        self.extract_long(patients_data_csv_filepath)

        zf = ZipFile(zip_filename, "w")
        zf.write(patients_data_csv_filepath, os.path.basename(patients_data_csv_filepath))
        zf.close()
        shutil.rmtree(task_dir)

        result = {"filepath": zip_filename,
                  "content_type": "text/csv",
                  "username": self.user.username,
                  "user_id": self.user.id,
                  "filename": self.zip_name,
                  }
        return result

    def _get_patients_in_users_groups(self):
        in_wgs = Q(working_groups__in=self.user.working_groups.all(), active=True)
        in_reg = Q(rdrf_registry__in=[self.registry])
        query = in_wgs & in_reg
        return Patient.objects.filter(query)

    def extract_long(self, patients_data_csv_filepath):
        patients = self._get_patients_in_users_groups()
        pids = [id for id in patients.values_list('id', flat=True)]
        self._write_patients_data(patients_data_csv_filepath, pids)

    @ cached(maxsize=None)
    def _match(self, cde_code):
        if self.all_cdes:
            return True
        for pattern in self.patterns:
            if cde_code.startswith(pattern):
                return True
        if cde_code in self.fields:
            return True
        return False

    def _get_sex_value(self, patient):
        sex_choices = {"1": "Male", "2": "Female", "3": "Indeterminate"}
        return sex_choices.get(patient.sex, "")

    def _get_field(self, pid, field):
        map_name = f"{field}_map"
        field_map = getattr(self, map_name)

        if pid in field_map:
            return field_map[pid]
        else:
            try:
                patient = Patient.objects.get(id=pid)
                if field == "deident":
                    value = getattr(patient, "deident")
                elif field == "dob":
                    value = aus_date(patient.date_of_birth)
                elif field == "sex":
                    value = self._get_sex_value(patient)

                field_map[pid] = value
                return value
            except Patient.DoesNotExist:
                field_map[pid] = "?"
                return "?"

    def _get_collection_date_map(self, cd: ClinicalData) -> dict:
        d = {}
        if cd.data and "forms" in cd.data:
            for f in cd.data["forms"]:
                form_name = f["name"]
                for s in f["sections"]:
                    if not s["allow_multiple"]:
                        for c in s["cdes"]:
                            if c["code"] == "COLLECTIONDATE":
                                value = c["value"]
                                date_value = aus_date_string(value)
                                d[form_name] = c["value"]
        return d

    def _yield_cdes(self, cd):
        # this will only work if there is one form with collection date
        pid = cd.django_id
        collection_date_map = self._get_collection_date_map(cd)
        response_type = get_response_type(cd)
        data = cd.data
        yield self._get_deident(pid)
        yield self._get_dob(pid)
        yield self._get_sex(pid)
        for f in data["forms"]:
            form_name = f["name"]
            collection_date = collection_date_map.get(form_name, "")
            for s in f["sections"]:
                section_code = s["code"]
                if not s["allow_multiple"]:
                    index = 1
                    for c in s["cdes"]:
                        code = c["code"]
                        cde_data = self._get_cde_data(pid, c, code, form_name, section_code,
                                                      collection_date, response_type, index)
                        if cde_data:
                            yield cde_data
                else:
                    for i, item in enumerate(s["cdes"]):
                        index = i + 1
                        for c in item:
                            code = c["code"]
                            cde_data = self._get_cde_data(pid, c, code, form_name, section_code,
                                                          collection_date, response_type, index)
                            if cde_data:
                                yield cde_data

    def _get_cde_data(self, pid, cde_dict, code, form_name, section_code, collection_date, response_type, index):
        if self._match(code):
            logger.debug(f"code {code} matches")
            questionnaire, question = get_questionnaire_number(code)
            cde = get_cde_model(code)
            name = cde.name
            value = cde_dict["value"]

            try:
                if type(value) is list:
                    display_value = ";".join([get_display_value(code, x) for x in value])
                else:
                    display_value = get_display_value(code, value)
            except Exception as ex:
                logger.error(f"error {code}: {ex}")
                display_value = "ERROR"
            return (pid,
                    form_name,
                    section_code,
                    code,
                    questionnaire,
                    question,
                    name,
                    display_value,
                    collection_date,
                    response_type,
                    index)  # index column

    def _write_patients_data(self, csv_path, pids):
        d = self.delimiter
        header = ResearchDownload.PATIENTS_DATA_HEADER.replace(",", d)

        with open(csv_path, "w") as f:
            f.write(header)
            for cd in yield_cds(pids):
                for t in self._yield_cdes(cd):
                    pid = t[0]
                    form_name = t[1]
                    qn = t[4]
                    q = t[5]
                    n = t[6]
                    v = t[7]
                    coll = t[8]
                    rt = t[9]
                    index = t[10]
                    line = f"{pid}{d}{qn}{d}{q}{d}{n}{d}{v}{d}{coll}{d}{rt}{d}{form_name}{d}{index}\n"
                    f.write(line)
