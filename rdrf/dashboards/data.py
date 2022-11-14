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
cdf = "COLLECTIONDATE"  # collection date field name
pid = "PID"  # patient id field name


class RegistryDataFrame:
    """
    Loads all data into a Pandas DataFrame for analysis
    """

    def __init__(self, registry, config, patient_id=None):
        self.registry = registry
        self.config = config
        self.patient_id = patient_id
        self.prefix_fields = ["pid", "seq", "type", "form"]
        self.prefix_names = ["PID", "SEQ", "TYPE", "FORM"]
        self.fields = self.config["fields"]
        self.num_fields = len(self.fields)
        self.column_names = self._get_column_names()
        self.dataframe_columns = self.prefix_names + self.column_names
        self.baseline_form = self.config["baseline_form"]
        self.followup_form = self.config["followup_form"]
        self.form_names = [self.baseline_form, self.followup_form]
        self.mode = "all" if patient_id is None else "single"
        self.field_map = {field: None for field in self.config["fields"]}

        a = datetime.now()
        logger.debug("getting dataframe")
        self.df = self._get_dataframe()
        b = datetime.now()
        self.df[cdf] = pd.to_datetime(self.df[cdf])
        c = datetime.now()
        logger.debug(f"time taken to generate df = {b-a}")
        logger.debug(f"time taken to convert dates  = {c-b}")
        self.df.to_csv("/data/patients-data.csv")

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

        return [field_map.get(field, None) for field in self.config["fields"]]

    @property
    def data(self):
        return self.df


def get_data(registry, pid=None):
    try:
        base_config = VisualisationBaseDataConfig.objects.get(registry=registry)
        config = base_config.config
    except VisualisationData.DoesNotExist:
        config = None

    rdf = RegistryDataFrame(registry, config, pid)
    return rdf.data
