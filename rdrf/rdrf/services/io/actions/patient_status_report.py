import logging
import csv
import json
from time import time
from datetime import date
from django.http import HttpResponse
from rdrf.models.definition.models import RegistryForm
from rdrf.models.definition.models import Section
from rdrf.models.definition.models import CommonDataElement
from rdrf.models.definition.models import ContextFormGroup
from rdrf.models.definition.models import ClinicalData
from rdrf.helpers.utils import cde_completed
from rdrf.helpers.utils import format_date
from rdrf.helpers.utils import parse_iso_date
from rdrf.helpers.utils import parse_iso_datetime
from registry.patients.models import Patient
from registry.patients.models import ConsentValue

logger = logging.getLogger(__name__)


class Dates:
    FAR_FUTURE = date(2100, 1, 1)
    DISTANT_PAST = date(1900, 1, 1)


class SecurityException(Exception):
    pass


class ReportParserException(Exception):
    pass


class ColumnType:
    DEMOGRAPHICS = "demographics"
    CDE = "cde"
    COMPLETION = "completion"
    COMPLETION_PERCENTAGE = "%"
    CONSENT = "consent"
    CONSENT_DATE = "consent_date"
    FOLLOWUP_DATE = "followup_date"


demographics_transform_map = {"sex": {"1": "Male", "2": "Female", "3": "Indeterminate"},
                              "date_of_birth": format_date,
                              }


def log_time_taken(f):
    def wrapper(*args, **kw):
        start_time = time()
        result = f(*args, **kw)
        finish_time = time()
        logger.info(f'The report: {args[2]} was generated in: {(finish_time - start_time):.2f} sec')
        return result
    return wrapper


def aus_date(american_date):
    if not american_date:
        return ""
    year, month, day = american_date.split("-")
    return "%s-%s-%s" % (day, month, year)


def get_date(datetime_string):
    dt = parse_iso_datetime(datetime_string)
    return dt.date()


def get_timestamp(clinical_data):
    if not clinical_data:
        return None
    if not clinical_data.data:
        return None

    return parse_iso_datetime(clinical_data.data.get("timestamp", None))


class ReportGenerator:
    def __init__(self, custom_action, registry_model, report_name, report_spec, user, input_data, run_async=False):
        self.run_async = run_async
        self.custom_action = custom_action
        self.runtime_spec = custom_action.spec
        self.registry_model = registry_model
        # filter models to use to restrict query (models)
        # The context form group model must be fixed if used
        # If None the default contexts will be used
        self.filter_context_form_group = None
        self.filter_form = None
        self.filter_section = None
        self.filter_cde = None
        self.report_name = report_name
        self.report_spec = json.loads(report_spec)
        self.has_filter = True
        self._parse_filter_spec(self.runtime_spec)
        self.user = user
        self.input_data = input_data  # this filters the data
        self.form_names = None
        self.start_value = None
        self.finish_value = None
        self.data = self._get_all_data()
        self.context_form_group = self._get_context_form_group()
        self.report = None
        self.has_valid_filter = False
        self._setup_inputs()

    def _setup_inputs(self):
        # todo allow different data types
        if self.input_data is not None:
            self.start_value = self.input_data.get("start_value", Dates.DISTANT_PAST)
            self.end_value = self.input_data.get("end_value", Dates.FAR_FUTURE)
            if isinstance(self.start_value, str):
                self.start_value = get_date(self.start_value)
            if isinstance(self.end_value, str):
                self.end_value = get_date(self.end_value)
            if self.start_value and self.end_value:
                self.has_valid_filter = True

    def _parse_filter_spec(self, runtime_spec_dict):
        if "filter_spec" in runtime_spec_dict:
            filter_spec = runtime_spec_dict["filter_spec"]
            if "filter_field" in filter_spec:
                filter_field = filter_spec["filter_field"]
                cfg_name = filter_field.get("context_form_group", None)
                if cfg_name is not None:
                    self.filter_context_form_group = ContextFormGroup.objects.get(registry=self.registry_model,
                                                                                  name=cfg_name)
                    if not self.filter_context_form_group.context_type == "F":
                        raise ValueError("filter context form group context type must be fixed")

                form_name = filter_field["form"]
                self.filter_form = RegistryForm.objects.get(registry=self.registry_model,
                                                            name=form_name)
                section_code = filter_field["section"]
                self.filter_section = self.filter_form.get_section_model(section_code)
                cde_code = filter_field["cde"]
                self.filter_cde = self.filter_section.get_cde(cde_code)
        else:
            self.has_filter = False

    def dump_csv(self, stream):
        writer = csv.writer(stream)
        writer.writerows(self.report)
        return stream

    @property
    def task_result(self):
        import os.path
        from rdrf.helpers.utils import generate_token
        from django.conf import settings
        task_dir = settings.TASK_FILE_DIRECTORY
        filename = generate_token()
        filepath = os.path.join(task_dir, filename)
        with open(filepath, "w") as f:
            logger.info("writing csv ...")
            self.dump_csv(f)
            logger.info("wrote csv ok")
        result = {"filepath": filepath,
                  "content_type": "text/csv",
                  "username": self.user.username,
                  "user_id": self.user.id,
                  "filename": f"{self.report_name}.csv",
                  }
        logger.info("result dict = %s" % result)
        return result

    def _get_context(self, patient_model):
        # get the fixed context associated with the context
        # form group specified in the report spec.
        # there should only be one for each patient
        context_models = patient_model.context_models
        return self._get_fixed_context(context_models)

    def _get_fixed_context(self, context_models):
        for context_model in context_models:
            if context_model.context_form_group:
                if context_model.context_form_group.pk == self.context_form_group.pk:
                    return context_model

    def _get_context_form_group(self):
        if "context_form_group" in self.report_spec:
            form_group_name = self.report_spec["context_form_group"]
            cfg = ContextFormGroup.objects.get(name=form_group_name,
                                               registry=self.registry_model,
                                               context_type="F")
            return cfg

    def _get_all_data(self):
        return []

    def generate_report(self):
        self._security_check()
        return self._run_report()

    def _run_report(self):
        rows = []
        rows.append(self._get_header())
        for patient_model in self._get_patients():
            try:
                logger.info("getting data for patient %s" % patient_model.pk)
                # the context needs to be determined by the report spec
                # as it contains the context_form_group name
                context_model = self._get_context(patient_model)
                if not context_model:
                    logger.info("no context - skipping")
                    continue
                logger.info("context id = %s" % context_model.id)
                data = self._load_patient_data(patient_model, context_model.id)
                if not data:
                    logger.info("no data")
                else:
                    logger.info("data exists")
                    row = []
                    for column in self.report_spec["columns"]:
                        column_value = "" if not data else self._get_column_value(patient_model, data, column)
                        row.append(column_value)
                    rows.append(row)
            except Exception as ex:
                logger.error("%s report error pid %s: %s" % (self.report_name, patient_model.pk, ex))
        self.report = rows

    def _get_header(self):
        def header(col):
            if "label" in col:
                return col["label"]
            return col["name"]
        return [header(col) for col in self.report_spec["columns"]]

    def _get_column_value(self, patient_model, data, column):
        column_type = column["type"]
        if column_type == ColumnType.DEMOGRAPHICS:
            column_name = column["name"]
            return self._get_demographics_column(patient_model, column_name)
        if column_type == ColumnType.COMPLETION:
            form_name = column["name"]
            return self._completed(patient_model, form_name, data)
        if column_type == ColumnType.COMPLETION_PERCENTAGE:
            form_name = column["name"]
            return self._completed(patient_model, form_name, data, percentage=True)
        if column_type == ColumnType.CDE:
            cde_path = column["name"]
            try:
                return self._get_cde(patient_model, cde_path, data)
            except KeyError:
                return "[Not Entered]"
        if column_type == ColumnType.CONSENT:
            consent_section_code, consent_code = column["name"].split("/")
            return self._get_consent(patient_model,
                                     consent_section_code,
                                     consent_code)
        if column_type == ColumnType.CONSENT_DATE:
            consent_section_code, consent_code = column["name"].split("/")
            return self._get_consent(patient_model,
                                     consent_section_code,
                                     consent_code,
                                     get_date=True)
        if column_type == ColumnType.FOLLOWUP_DATE:
            context_form_group_name = column["context_form_group"]
            form_name = column["name"]
            return self._get_followup_date(patient_model,
                                           context_form_group_name,
                                           form_name)
        else:
            raise ReportParserException("Unknown column type: %s" % column_type)

    def _get_followup_date(self,
                           patient_model,
                           context_form_group_name,
                           form_name):
        from rdrf.models.definition.models import ContextFormGroup
        cfg = ContextFormGroup.objects.get(registry=self.registry_model,
                                           name=context_form_group_name)
        # find the last/latest context containing the form
        context_models = [c for c in patient_model.context_models
                          if c.registry.pk == self.registry_model.pk and c.context_form_group and c.context_form_group.pk == cfg.pk]
        if not context_models:
            return ""
        latest_date = None
        for context_model in context_models:
            # get the associated clinical data and check the timestamp
            try:
                clinical_data = ClinicalData.objects.get(context_id=context_model.pk,
                                                         django_model="Patient",
                                                         collection="cdes",
                                                         django_id=patient_model.pk)
                timestamp = get_timestamp(clinical_data)
                if latest_date is None or timestamp > latest_date:
                    latest_date = timestamp
            except ClinicalData.DoesNotExist:
                pass
        if latest_date is None:
            return ""
        return format_date(latest_date)

    def _get_consent(self,
                     patient_model,
                     consent_section_code,
                     consent_code,
                     get_date=False):
        for consent_section in self.registry_model.consent_sections.all():
            if consent_section.code == consent_section_code:
                for consent_question in consent_section.questions.all():
                    if consent_question.code == consent_code:
                        try:
                            consent_value = ConsentValue.objects.get(patient=patient_model,
                                                                     consent_question=consent_question)
                            if get_date:
                                first_save = consent_value.first_save
                                last_update = consent_value.last_update
                                if not last_update:
                                    return format_date(first_save)
                                return format_date(last_update)
                            return "True" if consent_value else "False"
                        except ConsentValue.DoesNotExist:
                            if get_date:
                                return ""
                            return "False"
        if get_date:
            return ""
        return "False"

    def _get_cde(self, patient_model, cde_path, data):
        if "/" in cde_path:
            form_name, section_code, cde_code = cde_path.split("/")
            form_model = RegistryForm.objects.get(name=form_name,
                                                  registry=self.registry_model)
            section_model = Section.objects.get(code=section_code)
            cde_model = CommonDataElement.objects.get(code=cde_code)
        else:
            form_model, section_model, cde_model = self._find_cde(cde_path)

        context_id = data["context_id"]
        raw_value = patient_model.get_form_value(self.registry_model.code,
                                                 form_model.name,
                                                 section_model.code,
                                                 cde_model.code,
                                                 context_id=context_id,
                                                 clinical_data=data,
                                                 flattened=False)
        if isinstance(raw_value, list):
            display_value = "|".join([str(cde_model.get_display_value(x)) for x in raw_value])
        else:
            display_value = cde_model.get_display_value(raw_value)
            if cde_model.datatype == "date":
                if not display_value:
                    return ""
                return format_date(display_value)

        return display_value

    def _find_cde(self, cde_code):
        for form_model in self.registry_model.forms:
            for section_model in form_model.section_models:
                for cde_model in section_model.cde_models:
                    if cde_model.code == cde_code:
                        return form_model, section_model, cde_model

        raise ReportParserException("Report cde %s not found" % cde_code)

    def _get_demographics_column(self, patient_model, column_name):
        transform = demographics_transform_map.get(column_name, None)
        raw_value = getattr(patient_model, column_name)
        if transform is None:
            return raw_value
        else:
            if isinstance(transform, dict):
                return transform[raw_value]
            return transform(raw_value)

    def _load_patient_data(self, patient_model, context_id):
        return patient_model.get_dynamic_data(self.registry_model,
                                              context_id=context_id)

    def _completed(self, patient_model, form_name, data, percentage=False):
        form_model = RegistryForm.objects.get(name=form_name,
                                              registry=self.registry_model)
        if not percentage:
            for section_model in form_model.section_models:
                if not section_model.allow_multiple:
                    for cde_model in section_model.cde_models:
                        if not cde_completed(self.registry_model,
                                             form_model,
                                             section_model,
                                             cde_model,
                                             patient_model,
                                             data):
                            return False
            return True
        # percentage
        num_cdes = 0.0
        num_completed = 0.0
        for section_model in form_model.section_models:
            if not section_model.allow_multiple:
                for cde_model in section_model.cde_models:
                    num_cdes += 1.0
                    if cde_completed(self.registry_model,
                                     form_model,
                                     section_model,
                                     cde_model,
                                     patient_model,
                                     data):
                        num_completed += 1.0
        value = 100.0 * (num_completed / num_cdes)
        return round(value, 0)

    def _get_patients(self):
        user_working_groups = self.user.working_groups.all()
        if not self.has_filter or not self.has_valid_filter:
            return Patient.objects.filter(rdrf_registry__code__in=[self.registry_model.code],
                                          working_groups__in=user_working_groups)
        else:
            def patient_iterator():
                for patient_model in Patient.objects.filter(rdrf_registry__code__in=[self.registry_model.code],
                                                            working_groups__in=user_working_groups):
                    if self._include_patient(patient_model):
                        yield patient_model
            return patient_iterator()

    def _include_patient(self, patient_model):
        filter_value = self._get_filter_value(patient_model)
        if filter_value is None:
            return False
        return filter_value >= self.start_value and filter_value <= self.end_value

    def _get_filter_value(self, patient_model):
        cds = patient_model.get_clinical_data_for_form_group(self.context_form_group.name)
        if cds:
            if len(cds) > 1:
                raise ValueError("There should only be one clinical data object")
            clinical_data = cds[0]
            return self._get_filter_field_value(clinical_data)
        else:
            # No data saved at all for any of forms in this form group
            return None

    def _get_filter_field_value(self, clinical_data):
        assert self.filter_form is not None, "Filter form is None"
        if clinical_data.data:
            forms = clinical_data.data["forms"]
            for form_dict in forms:
                if form_dict["name"] == self.filter_form.name:
                    for section_dict in form_dict["sections"]:
                        if section_dict["code"] == self.filter_section.code:
                            for cde_dict in section_dict["cdes"]:
                                if cde_dict["code"] == self.filter_cde.code:
                                    value = cde_dict["value"]
                                    return parse_iso_date(value)

    def _security_check(self):
        if not self.user.in_registry(self.registry_model):
            raise SecurityException()


@log_time_taken
def execute(custom_action, registry_model, report_name, report_spec, user, input_data=None, runtime_spec={}, run_async=False):
    logger.info("running custom action report %s for %s" % (report_name,
                                                            user.username))
    parser = ReportGenerator(custom_action, registry_model, report_name, report_spec, user, input_data, run_async)
    parser.generate_report()
    if not run_async:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{report_name}.csv"'
        return parser.dump_csv(response)
    else:
        return parser.task_result
