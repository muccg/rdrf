import pandas as pd
from rdrf.models.definition.models import Registry
from rdrf.models.definition.models import ClinicalData
from rdrf.models.definition.models import RDRFContext
from rdrf.models.definition.models import ContextFormGroup

from rdrf.models.proms.models import Survey
from registry.patients.models import Patient

from datetime import datetime, timedelta
from itertools import chain
from rdrf.helpers.utils import parse_iso_datetime

from .models import VisualisationBaseDataConfig

import logging

logger = logging.getLogger(__name__)


def get_display_value(cde_code, raw_value):
    return raw_value


def cde_iterator(registry):
    for form in registry.forms:
        for section in form.section_models:
            for cde in section.cde_models:
                yield cde


# Abbreviations
cdf = "COLLECTIONDATE"  # collection date field
pid = "PID"  # patient id


class RegistryDataFrame:
    """
    Loads all data into a Pandas DataFrame for analysis
    """

    def __init__(self, registry, config_model, patient_id=None):
        self.registry = registry
        self.config_model = config_model
        if self.config_model.state == "D":
            logger.debug("reading json ...")
            t1 = datetime.now()
            self.df = pd.read_json(self.config_model.data)
            t2 = datetime.now()
            logger.debug("time to load json = {t2-t1}")
            return

        # no data loaded
        self.patient_id = patient_id
        self.prefix_fields = ["pid", "seq", "type", "form"]
        self.prefix_names = ["PID", "SEQ", "TYPE", "FORM"]
        self.fields = self.config_model.config["fields"]
        self.num_fields = len(self.fields)
        self.column_names = self._get_column_names()
        self.dataframe_columns = self.prefix_names + self.column_names
        self.baseline_form = self.config_model.config["baseline_form"]
        self.followup_form = self.config_model.config["followup_form"]
        self.form_names = [self.baseline_form, self.followup_form]
        self.mode = "all" if patient_id is None else "single"
        self.field_map = {field: None for field in self.config_model.config["fields"]}

        a = datetime.now()
        logger.debug("getting dataframe")
        self.df = self._get_dataframe()
        b = datetime.now()
        self.df[cdf] = pd.to_datetime(self.df[cdf])
        self.df = self._assign_correct_seq_numbers(self.df)
        c = datetime.now()
        logger.debug(f"time taken to generate df = {b-a}")
        logger.debug(f"time taken to convert dates  = {c-b}")
        self.config_model.data = self.df.to_json()
        self.config_model.state = "D"
        self.config_model.save()

    def _assign_correct_seq_numbers(self, df) -> pd.DataFrame:
        """
        If patients miss followups, naively taking the existing
        sequence of followups ( 0,1,2 etc as (e,g)  baseline, 6 months, 12 months
        will be wrong.
        If the baseline collection date is known ( call it B) and the
        schedule is known ( e.g. every 6 months) then we can calculate the expected
        collection dates as : B+6 months, B+12 months etc.
        If a patient P has missed a followup but the collection date of a followup
        is closest to a schedule date D with seq number i, we assign i to it
        instead of counting 0,1,2..
        """
        return df  # todo

    def _get_column_names(self):
        cols = []
        for field in self.fields:
            column_name = self._get_column_name(field)
            cols.append(column_name)
        logger.debug(f"column_names = {cols}")
        return cols

    def _get_column_name(self, field):
        return field

    def _sanity_check_cd(self, cd):
        return cd.data and "forms" in cd.data

    def _get_cd_type(self, cd):
        context_id = cd.context_id
        context = RDRFContext.objects.get(id=context_id)
        if context.context_form_group:
            if context.context_form_group.context_type == "F":
                return "baseline"
            else:
                return "followup"

    def _get_cd_data(self, cd, form_name):
        if not self._sanity_check_cd(cd):
            return [None] * self.num_cdes
        else:
            return self._get_fields(form_name, cd)

    def _get_form(self, cd_type):
        if cd_type == "baseline":
            return self.baseline_form
        else:
            return self.followup_form

    def _get_patient_rows(self, patient):
        rows = []
        pid = patient.id
        for seq, cd in enumerate(self._get_cds(patient)):
            row = [pid, seq]
            cd_type = self._get_cd_type(cd)
            row.append(cd_type)
            form_name = self._get_form(cd_type)
            row.append(form_name)
            field_row = self._get_cd_data(cd, form_name)
            if field_row is None:
                field_row = [None] * self.num_fields
            row.extend(field_row)
            rows.append(row)
        return rows

    def _get_cds(self, patient):
        return ClinicalData.objects.filter(
            collection="cdes", django_id=patient.id
        ).order_by("context_id")

    def _get_dataframe(self):
        rows = []
        if self.mode == "all":
            qry = Patient.objects.all().order_by("id")
        else:
            qry = Patient.objects.filter(id=self.patient_id)

        for patient in qry:
            for row in self._get_patient_rows(patient):
                rows.append(row)
        df = pd.DataFrame(rows)
        df.columns = self.dataframe_columns
        return df

    def _get_fields(self, form_name, cd):
        field_map = self.field_map.copy()

        for form_dict in cd.data["forms"]:
            if form_dict["name"] == form_name:
                for section_dict in form_dict["sections"]:
                    if not section_dict["allow_multiple"]:
                        for cde_dict in section_dict["cdes"]:
                            cde_code = cde_dict["code"]
                            if cde_code in field_map:
                                raw_value = cde_dict["value"]
                                field_map[cde_code] = get_display_value(
                                    cde_code, raw_value
                                )

        return [
            field_map.get(field, None) for field in self.config_model.config["fields"]
        ]

    @property
    def data(self):
        return self.df


def get_data(registry, pid=None):
    try:
        config = VisualisationBaseDataConfig.objects.get(registry=registry)
    except VisualisationData.DoesNotExist:
        config = None

    rdf = RegistryDataFrame(registry, config, pid)

    return rdf.data
