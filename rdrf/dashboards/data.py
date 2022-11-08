import pandas as pd
from rdrf.models.definition.models import Registry
from rdrf.models.definition.models import ClinicalData
from rdrf.models.proms.models import Survey
from registry.patients.models import Patient

from datetime import datetime, timedelta
from itertools import chain
from rdrf.helpers.utils import parse_iso_datetime


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


def get_rows(spec):
    """
                  SEQ|PID| CDE1 |CDE2 ..|COLLECTIONDATE|
    baseline      1  | 1 | 3    | ...
    followup1     2  | 1 | 6    |
    followup2     3  | 1 | 4    |
    """

    # sequential version
    for p in Patient.objects.all():
        cds = ClinicalData.objects.filter(collection="cdes", django_id=p.id).order_by(
            "context_id"
        )

        baseline_row = get_baseline(spec, cds)
        yield baseline_row
        followup_rows = get_followup_rows(spec, cds)
        for followup_row in followup_rows:
            yield followup_row


def get_df(spec):
    df = pd.DataFrame((tuple(t) for t in get_rows(spec)))
