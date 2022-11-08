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


def get_display_value(cde_code, raw_value):
    return raw_value


class RegistryDataFrame:
    """
    Loads all data into a Pandas DataFrame for analysis
    """

    def __init__(self, registry, spec, patient_id=None):
        self.spec = spec
        self.fields = self.spec["fields"]
        self.num_fields = len(self.fields)
        self.registry = registry
        self.baseline_form = self.spec["baseline_form"]
        self.followup_form = self.spec["followup_form"]
        self.collection_date_field = "COLLECTIONDATE"
        self.column_names = self._get_column_names()
        self.form_names = [self.baseline_form, self.followup_form]

        if patient_id is None:
            self.mode = "all"
        else:
            self.mode = "single"
            self.patient_id = patient_id

        self.df = self._get_dataframe()
        self.df[self.collection_date_field] = pd.to_datetime(
            self.df[self.collection_date_field]
        )

    def _get_column_names(self):
        cols = ["seq", "pid", "type", "form"]
        for field in self.fields:
            column_name = self._get_column_name(field)
            cols.append(column_name)
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
            return [None] * self.num_fields
        else:
            return [
                self._get_field(form_name, field, cd) for field in self.spec["fields"]
            ]

    def _get_form(self, cd_type):
        if cd_type == "baseline":
            return self.baseline_form
        else:
            return self.followup_form

    def _get_patient_rows(self, patient):
        rows = []
        pid = patient.id
        for index, cd in enumerate(self._get_cds(patient)):
            row = [index + 1, pid]
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
        df.columns = self.column_names
        return df

    def _get_field(self, form_name, field, cd):
        for form_dict in cd.data["forms"]:
            if form_dict["name"] == form_name:
                for section_dict in form_dict["sections"]:
                    if not section_dict["allow_multiple"]:
                        for cde_dict in section_dict["cdes"]:
                            if cde_dict["code"] == field:
                                raw_value = cde_dict["value"]
                                display_value = get_display_value(field, raw_value)
                                return display_value

    def types_of_forms_completed(self, cutoff):
        df = self.df[self.df[self.collection_date_field] >= cutoff]
        counts = df.value_counts("form", normalize=True)
        return 100 * counts  # percentages
