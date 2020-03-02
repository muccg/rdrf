from rdrf.helpers.utils import cde_completed
from rdrf.models.definition.models import Registry
from rdrf.models.definition.models import RegistryForm
from rdrf.models.definition.models import ClinicalData
from rdrf.models.definition.models import ContextFormGroup
from rdrf.models.definition.models import RDRFContext
from registry.patients.models import Patient
from registry.groups.models import WorkingGroup
import logging
from django.http import HttpResponse

logger = logging.getLogger(__name__)


class SecurityException(Exception):
    pass


class ReportParserException(Exception):
    pass


class ColumnType:
    DEMOGRAPHICS = "demographics"
    CDE = "cde"
    COMPLETION = "completion"


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

    def _get_context(self, patient_model):
        # get the fixed context associated with the context
        # form group specified in the report spec.
        # there should only be one for each patient
        context_models = RDRFContext.objects.filter(registry=self.registry_model,
                                                    context_form_group=self.context_form_group)
        if len(context_models) == 1:
            logger.debug("found context")
            return context_models[0]

    def _get_context_form_group(self):
        # return None to indicate no group
        if "context_form_group" in self.report_spec:
            form_group_name = self.report_spec["context_form_group"]
            return ContextFormGroup.objects.get(name=form_group_name,
                                                registry=self.registry_model,
                                                context_type="F")

    def _get_all_data(self):
        return []

    def generate_report(self):
        self._security_check()
        self._parse_spec()
        return self._run_report()

    def _run_report(self):
        rows = []
        rows.append(self._get_header())
        for patient_model in self._get_patients():
            data = self._load_patient_data(patient_model)
            row = []
            for column in self.report_spec["columns"]:
                column_value = self._get_column_value(patient_model, data, column)
                row.append(column_value)
            rows.append(row)
        logger.debug(rows)
        return HttpResponse(str(rows))

    def _get_header(self):
        def h(col):
            if "label" in col:
                return col["label"]
            else:
                return col["name"]
        return [h(col) for col in self.report_spec["columns"]]

    def _get_column_value(self, patient_model, data, column):
        column_type = column["type"]
        if column_type == ColumnType.DEMOGRAPHICS:
            column_name = column["name"]
            return self._get_demographics_column(patient_model, column_name)
        if column_type == ColumnType.COMPLETION:
            form_name = column["name"]
            return self._completed(patient_model, form_name, data)
        if column_type == ColumnType.CDE:
            cde_path = column["name"]
            try:
                return self._get_cde(patient_model, cde_path, data)
            except KeyError:
                return "[Not Entered]"
        else:
            raise ReportParserException("Unknown column type: %s" % column_type)

    def _get_cde(self, patient_model, cde_path, data):
        if "/" in cde_path:
            form_name, section_code, cde_code = cde_path.split("/")
            form_model = RegistryForm.objects.get(name=form_name,
                                                  registry=self.registry_model)
            section_model = Section.objects.get(code=section_code)
            cde_model = CommonDataElement.objects.get(code=cde_code)
        else:
            form_model, section_model, cde_model = self._find_cde(cde_path)

        context_model = self._get_context(patient_model)
        if context_model:
            raw_value = patient_model.get_form_value(self.registry_model.code,
                                                     form_model.name,
                                                     section_model.code,
                                                     cde_model.code,
                                                     context_id=context_model.id,
                                                     clinical_data=data)
        else:
            # this will search the default context
            raw_value = patient_model.get_form_value(self.registry_model.code,
                                                     form_model.name,
                                                     section_model.code,
                                                     cde_model.code,
                                                     clinical_data=data)

        return cde_model.get_display_value(raw_value)

    def _find_cde(self, cde_code):
        for form_model in self.registry_model.forms:
            for section_model in form_model.section_models:
                if not section_model.allow_multiple:
                    for cde_model in section_model.cde_models:
                        if cde_model.code == cde_code:
                            return form_model, section_model, cde_model

        raise ReportParserException("Report cde %s not found or not unique in registry" % cde_code)

    def _get_demographics_column(self, patient_model, column_name):
        return getattr(patient_model, column_name)

    def _load_patient_data(self, patient_model):
        return patient_model.get_dynamic_data(self.registry_model)

    def _completed(self, patient_model, form_name, data):
        form_model = RegistryForm.objects.get(name=form_name,
                                              registry=self.registry_model)
        for section_model in form_model.section_models:
            if not section_model.allow_multiple:
                for cde_model in section_model.cde_models:
                    if not cde_completed(self.registry_model, form_model, section_model, cde_model, patient_model, data):
                        return False
        return True

    def _get_patients(self):
        user_working_groups = self.user.working_groups.all()

        for patient_model in Patient.objects.filter(rdrf_registry__code__in=[self.registry_model.code],
                                                    working_groups__in=user_working_groups):
            yield patient_model

    def _parse_spec(self):
        if "columns" in self.report_spec:
            self.columns = [self._parse_column(column_spec) for column_spec in self.report_spec["columns"]]
        else:
            self.columns = []

    def _parse_column(self, column_spec):
        column_name = column_spec["name"]
        column_type = column_spec["type"]
        if column_type == "field":
            field_location = column_spec["location"]
            retriever = self._get_retriever(field_location)
            return {"name": column_name,
                    "retriever": retriever}

    def _security_check(self):
        if not self.user.in_registry(self.registry_model):
            raise SecurityException()


def execute(registry_model, report_name,  report_spec, user):
    parser = ReportGenerator(registry_model, report_name, report_spec, user)
    report = parser.generate_report()
    if report:
        return report
    else:
        response = HttpResponse()

    return response
