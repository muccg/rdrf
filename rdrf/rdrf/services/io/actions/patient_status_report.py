from rdrf.helpers.utils import cde_completed
from rdrf.models.definition.models import Registry
from rdrf.models.definition.models import RegistryForm
from registry.patients.models import Patient
from registry.groups.models import WorkingGroup


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
        self.registry_model = registry_model
        self.report_name = report_name
        self.report_spec = report_spec
        self.user = user
        self.form_names = None
        self.start_date = None
        self.finish_date = None

    def generate_report(self):
        self._security_check()
        self._parse_spec()
        return self._run_report()

    def _run_report(self):
        rows = []
        for patient_model in self._get_patients():
            data = self._load_patient_data(patient_model)
            row = []
            for column in self.report_spec["columns"]:
                column_value = self._get_column_value(patient_model, data, column)
                row.append(column_value)
            rows.append(row)

    def _get_column_value(self, patient_model, data, column):
        column_type = column["type"]
        if column_type == ColumnType.DEMOGRAPHICS:
            column_name = column["name"]
            return self._get_demographics_column(patient_model, column_name)
        elif column_type == ColumnType.COMPLETION:
            form_name = column["name"]
            return self._completed(patient_model, form_name, data)
        elif column_type == ColumnType.CDE:
            pass
        else:
            raise ReportParserException("Unknown column type: %s" % column_type)

    def _get_demographics_column(self, patient_model, column_name):
        return getattr(patient_model, column_name)

    def _load_patient_data(self, patient_model):
        return patient_model.get_dynamic_data(self.registry_model)

    def _completed(self, patient_model, form_name, data):
        form_model = RegistryForm.objects.get(name=form_name,
                                              registry=self.registry_model)
        for section_model in form_model.section_models:
            if not section_model.allow_mutliple:
                for cde_model in section_model.cde_models:
                    if not cde_completed(self.registry_model, form_model, section_model, cde_model, patient_model, data):
                        return False
        return True

    def _get_patients(self):
        user_working_groups = self.user.working_groups.filter(registry__in=[self.registry_model])

        for patient_model in Patient.objects.filter(rdrf_registry__in=[self.registry_model],
                                                    working_groups__in=[user_working_groups]):
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
