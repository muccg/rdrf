from django.http import HttpResponse
from rdrf.models.definition.models import RegistryForm
from rdrf.models.definition.models import Section
from rdrf.models.definition.models import CommonDataElement
from rdrf.models.definition.models import ContextFormGroup
from rdrf.models.definition.models import RDRFContext
from rdrf.models.definition.models import ClinicalData
from rdrf.helpers.utils import cde_completed
from rdrf.helpers.utils import format_date
from registry.patients.models import Patient
from registry.patients.models import ConsentValue
import logging
import csv

logger = logging.getLogger(__name__)


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


def aus_date(american_date):
    if not american_date:
        return ""
    year, month, day = american_date.split("-")
    return "%s-%s-%s" % (day, month, year)


def get_timestamp(clinical_data):
    from rdrf.helpers.utils import parse_iso_datetime
    if not clinical_data:
        return None
    if not clinical_data.data:
        return None

    return parse_iso_datetime(clinical_data.data.get("timestamp", None))


class ReportGenerator:
    def __init__(self, registry_model, report_name, report_spec, user):
        import json
        self.registry_model = registry_model
        self.report_name = report_name
        self.report_spec = json.loads(report_spec)
        self.user = user
        self.form_names = None
        self.start_date = None
        self.finish_date = None
        self.data = self._get_all_data()
        self.context_form_group = self._get_context_form_group()
        self.report = None

    def dump_csv(self, stream):
        writer = csv.writer(stream)
        writer.writerows(self.report)
        return stream

    def _get_context(self, patient_model):
        # get the fixed context associated with the context
        # form group specified in the report spec.
        # there should only be one for each patient
        context_models = RDRFContext.objects.filter(registry=self.registry_model,
                                                    object_id=patient_model.id,
                                                    context_form_group=self.context_form_group)
        num_contexts = len(context_models)
        if num_contexts == 1:
            return context_models[0]

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
            # the context needs to be determined by the report spec
            # as it contains the context_form_group name
            context_model = self._get_context(patient_model)
            data = self._load_patient_data(patient_model, context_model.id)
            row = []
            for column in self.report_spec["columns"]:
                column_value = self._get_column_value(patient_model, data, column)
                row.append(column_value)
            rows.append(row)
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

        for patient_model in Patient.objects.filter(rdrf_registry__code__in=[self.registry_model.code],
                                                    working_groups__in=user_working_groups):
            yield patient_model

    def _security_check(self):
        if not self.user.in_registry(self.registry_model):
            raise SecurityException()


def execute(registry_model, report_name, report_spec, user):
    logger.info("running custom action report %s for %s" % (report_name,
                                                            user.username))
    parser = ReportGenerator(registry_model, report_name, report_spec, user)
    parser.generate_report()
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="Completion Report.csv"'
    return parser.dump_csv(response)
