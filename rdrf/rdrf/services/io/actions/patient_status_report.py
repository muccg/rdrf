from rdrf.models.definition.models import Registry
from rdrf.models.definition.models import RegistryForm
from rdrf.models.definition.models import Section
from rdrf.models.definition.models import CommonDataElement
from rdrf.models.definition.models import ClinicalData
from rdrf.models.definition.models import ContextFormGroup
from rdrf.models.definition.models import RDRFContext
from rdrf.helpers.utils import cde_completed
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
                                                    object_id=patient_model.id,
                                                    context_form_group=self.context_form_group)
        l = len(context_models)
        logger.debug("num contexts found = %s" % l)
        if l == 1:
            logger.debug("found context - the context id is %s" % context_models[0].id)
            return context_models[0]

        logger.debug("context not found ( will use default )")

    def _get_context_form_group(self):
        # return None to indicate no group
        if "context_form_group" in self.report_spec:
            form_group_name = self.report_spec["context_form_group"]
            cfg = ContextFormGroup.objects.get(name=form_group_name,
                                               registry=self.registry_model,
                                               context_type="F")
            logger.debug("found context form group")
            return cfg

        logger.debug("no context form group")

    def _get_all_data(self):
        return []

    def generate_report(self):
        self._security_check()
        return self._run_report()

    def _run_report(self):
        rows = []
        rows.append(self._get_header())
        for patient_model in self._get_patients():
            logger.debug("creating row for patient %s ..." % patient_model.id)
            # the context needs to be determined by the report spec
            # as it contains the context_form_group name
            context_model = self._get_context(patient_model)
            data = self._load_patient_data(patient_model, context_model.id)
            row = []
            for column in self.report_spec["columns"]:
                logger.debug("getting column %s" % column["name"])
                column_value = self._get_column_value(patient_model, data, column)
                row.append(column_value)
            rows.append(row)
            logger.debug("***********************************")
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

        logger.debug("getting %s %s %s" % (form_model.name,
                                           section_model.code,
                                           cde_model.code))
        context_id = data["context_id"]
        logger.debug("searching context %s" % context_id)
        raw_value = patient_model.get_form_value(self.registry_model.code,
                                                 form_model.name,
                                                 section_model.code,
                                                 cde_model.code,
                                                 context_id=context_id,
                                                 clinical_data=data,
                                                 flattened=False)
        logger.debug("raw_value = %s" % raw_value)
        display_value = cde_model.get_display_value(raw_value)
        logger.debug("display_value = %s" % display_value)
        return display_value

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

    def _load_patient_data(self, patient_model, context_id):
        return patient_model.get_dynamic_data(self.registry_model,
                                              context_id=context_id)

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
