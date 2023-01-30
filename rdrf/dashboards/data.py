import pandas as pd
from rdrf.models.definition.models import ClinicalData
from rdrf.models.definition.models import RDRFContext
from rdrf.models.definition.models import CommonDataElement

from registry.patients.models import Patient

from datetime import datetime

from .models import VisualisationBaseDataConfig
from .utils import get_seq_name

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
SEQ = "SEQ"


class RegistryDataFrame:
    """
    Loads all data into a Pandas DataFrame for analysis
    """

    def __init__(
        self,
        registry,
        config_model,
        patient_id=None,
        force_reload=False,
        needs_all=False,
    ):
        self.registry = registry
        self.state = None
        self.config_model = config_model
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
        self.needs_all = needs_all

        a = datetime.now()
        if self.mode == "all" and force_reload:
            logger.info("forcing reload of dataframe..")
            self._reload_dataframe()
        elif self.mode == "all":
            logger.info("loading dataframe from base config json")
            self.df = pd.read_json(self.config_model.data)
            self.df[cdf] = pd.to_datetime(self.df[cdf], unit="ms")
            logger.debug(f"json cdf = {self.df[cdf]}")
        elif self.mode == "single":
            self._reload_dataframe()

        c = datetime.now()
        logger.info(f"time taken to load/generate df = {(c-a).total_seconds()} seconds")

    def _reload_dataframe(self):
        try:
            self.df = self._get_dataframe()
            if self.df is None:
                self.state = "empty"
            else:
                self.state = "ok"

            if self.state == "empty":
                return

        except ValueError as ve:
            msg = ve.message
            if "0 elements" in msg:
                logger.debug("no data?")

        self.df[cdf] = pd.to_datetime(self.df[cdf])
        self.df = self._assign_correct_seq_numbers(self.df)
        self.df = self._assign_seq_names(self.df)

    def _assign_seq_names(self, df):
        def get_aus_date(row):
            try:
                d = row["COLLECTIONDATE"].date()
                aus_date = f"{d.day}-{d.month}-{d.year}"
                if "nan" in aus_date:
                    return ""
                return f" ({aus_date})"
            except KeyError:
                return ""
            except ValueError:
                return ""

        df["SEQ_NAME"] = df.apply(
            lambda row: get_seq_name(row["SEQ"]) + get_aus_date(row), axis=1
        )
        return df

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

        def get_patients(df):
            return df["pid"].unique()

        def fix_baseline_for_patient(pid, df):
            return df

        def fix_missing_baseline(df):
            for pid in get_patients(df):
                df = fix_baseline_for_patient(pid, df)
            return df

        def fix_skipped(df):
            return df

        # df = fix_missing_baseline(df)
        # df = fix_skipped(df)

        return df  # todo

    def _get_column_names(self):
        cols = []
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
        if len(rows) == 0:
            return None
        df = pd.DataFrame(rows)
        df.columns = self.dataframe_columns
        return df

    def _get_fields(self, form_name, cd):
        field_map = self.field_map.copy()
        if not cd.data or "forms" not in cd.data:
            form_dicts = []
        else:
            form_dicts = cd.data["forms"]

        for form_dict in form_dicts:
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


def get_data(registry, patient=None, needs_all=False):
    try:
        config = VisualisationBaseDataConfig.objects.get(registry=registry)
    except VisualisationBaseDataConfig.DoesNotExist:
        config = None

    pid = None if patient is None else patient.id

    rdf = RegistryDataFrame(registry, config, pid, needs_all)

    return rdf.data


def lookup_cde_value(cde_code, raw_value):
    cde_model = CommonDataElement.objects.get(code=cde_code)
    if cde_model.pv_group:
        g = cde_model.pv_group.as_dict()
        values = g["values"]
        for d in values:
            if d["code"] == str(raw_value):
                return d["value"]
        if raw_value == "":
            return "Blank"
    return raw_value


def get_cde_values(cde_code):
    cde_model = CommonDataElement.objects.get(code=cde_code)
    if cde_model.pv_group:
        g = cde_model.pv_group.as_dict()
        dicts = g["values"]
        return [d["value"] for d in dicts]  # value is the display value
    else:
        return []


def get_percentages_within_seq(df, field):
    # produce grouped dataframe showing counts of field values
    g = df.groupby([SEQ, field]).agg({field: "count"})
    # add percentage within group
    g["PERCENTAGE"] = 100.00 * g[field] / g.groupby(SEQ)[field].transform("sum")

    # this will be the percentages of individual choices for a field for each
    # seq ( ie, baseline, followup 1, follow up 2...
    #   SEQ	EORTCQLQC29_Q31
    # 0	0	1279	25.564661
    #   1	1306	26.104337
    #   2	1187	23.725765
    #   3	1231	24.605237
    # 1	0	1235	24.685189
    # ...	...	...	...
    # 319	3	1327	26.529388
    # 20	0	1255	25.089964
    # 1	1276	25.509796
    # 2	1216	24.310276
    # 3	1255	25.089964
    return g


def combine_data(indiv_data: pd.DataFrame, avg_data: pd.DataFrame) -> pd.DataFrame:
    """
    This function takes individual patient scores for scale groups  and combines
    with a dataframe of average data for the same scores to produce a single dataframe
    showing the average data scores as avg_score_0 avg_score_1 etc.
    I use a left join as if a patient has only completed 2 followups we're only interested
    in the comparison with the average of those ( even if other patients have completed three for
    example.)
    """
    # [DEBUG:2022-12-13 10:54:17,541:sgc.py:91:get_graphic] average scores =    SEQ     score_0
    # runserver_1     | 0    0   66.666667
    # runserver_1     | 1    1  100.000000
    # runserver_1     | 2    2  100.000000
    # runserver_1     | 3    3   33.333333
    # runserver_1     | [DEBUG:2022-12-13 10:54:17,655:sgc.py:153:get_table] data =
    # runserver_1     |     PID  SEQ      TYPE  ...      SEQ_NAME     score_0    score_1
    # runserver_1     | 0  1032    0  baseline  ...      Baseline   66.666667  54.166667
    # runserver_1     | 1  1032    1  followup  ...  1st Followup  100.000000  29.166667
    # runserver_1     | 2  1032    2  followup  ...  2nd Followup  100.000000  33.333333
    # runserver_1     | 3  1032    3  followup  ...  3rd Followup   33.333333  83.333333

    avg_data = avg_data.rename(
        columns={
            col: "avg_" + col for col in avg_data.columns if col.startswith("score_")
        }
    )
    # now merge on SEQ column

    combined_data = indiv_data.merge(avg_data, how="left", on="SEQ")
    return combined_data
