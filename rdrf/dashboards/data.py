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


class DataLoader:
    def __init__(self, registry, spec):
        self.spec = spec
        self.fields = self.spec["fields"]
        self.num_fields = len(self.fields)
        self.registry = registry
        self.baseline_form = self.spec["baseline_form"]
        self.followup_form = self.spec["followup_form"]

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

    def get_dataframe(self):
        rows = []
        for patient in Patient.objects.all().order_by("id"):
            for row in self._get_patient_rows(patient):
                rows.append(row)
        return pd.DataFrame(rows)

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


def _get_survey_forms(cd: ClinicalData, survey_names, cutoff: datetime):
    for form_dict in cd.data["forms"]:
        if form_dict["name"] not in survey_names:
            continue
        for section_dict in form_dict["sections"]:
            if not section_dict["allow_multiple"]:
                for cde_dict in section_dict["cdes"]:
                    if cde_dict["code"] == "COLLECTIONDATE":
                        collection_date = parse_iso_datetime(cde_dict["value"])
                        if collection_date >= cutoff:
                            form_name = form_dict["name"]
                            pid = cd.django_id
                            data = form_dict
                            yield pid, form_name, collection_date, data


def get_surveys(survey_names, cutoff):
    cds = ClinicalData.objects.filter(collection="cdes")

    def has_data(cd):
        return cd.data and "forms" in cd.data

    return chain(
        *[_get_survey_forms(cd, survey_names, cutoff) for cd in cds if has_data(cd)]
    )


def get_survey_counts(survey_names, cutoff):
    counts = {survey_name: 0 for survey_name in survey_names}
    for t in get_surveys(survey_names, cutoff):
        if t:
            form_name = t[1]
            counts[form_name] += 1
    return counts


def get_types_of_forms_completed_data(registry_model: Registry) -> dict:
    t = datetime.now()
    one_week = timedelta(days=7)
    week_ago = t - one_week
    surveys = Survey.objects.filter(registry=registry_model)

    survey_names = [s.form.name for s in surveys]

    display_names = {s.form.name: s.form.display_name for s in surveys}
    counts_dict = get_survey_counts(survey_names, week_ago)
    return {
        display_names[survey_name]: counts_dict[survey_name]
        for survey_name in survey_names
    }


def get_rows(registry, spec):
    """
                  SEQ|PID| CDE1 |CDE2 ..|COLLECTIONDATE|
    baseline      1  | 1 | 3    | ...
    followup1     2  | 1 | 6    |
    followup2     3  | 1 | 4    |
    """
    triples = get_triples(registry, spec)

    # sequential version
    for p in Patient.objects.all():
        cds = ClinicalData.objects.filter(collection="cdes", django_id=p.id).order_by(
            "context_id"
        )

        baseline_row = get_baseline(triples, p, cds)
        yield baseline_row
        followup_rows = get_followup_rows(spec, cds)
        for followup_row in followup_rows:
            yield followup_row
