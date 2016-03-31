from rdrf.utils import get_cde_value
import openpyxl as xl
import logging

logger = logging.getLogger("registry_log")


class SpreadSheetReportFormat:
    WIDE = "WIDE"
    LONG = "LONG"


class SpreadSheetReportType:
    CURRENT = "CURRENT"
    LONGITUDINAL = "LONGITUDINAL"


def default_time_window():
    from datetime import datetime, timedelta
    one_year = timedelta(days=365)
    today = datetime.now()
    one_year_ago = today - one_year
    return (one_year_ago, today)


class SpreadSheetReport(object):

    def __init__(self,
                 user,
                 registry_model,
                 working_groups,
                 cde_triples,
                 time_window=default_time_window(),
                 report_format=SpreadSheetReportFormat.WIDE,
                 mongo_client=None,
                 testing=False):
        self.user = user
        self.output_filename = "%s_report.xlsx" % registry_model.code
        self.work_book = None
        self.working_groups = working_groups
        self.registry_model = registry_model
        self.report_format = report_format
        if time_window is None:
            self.report_type = SpreadSheetReportType.CURRENT
        else:
            self.report_type = SpreadSheetReportType.LONGITUDINAL

        # pair of datetimes (start, finish) ( inclusive)
        self.time_window = time_window
        self.cdes_triples = cde_triples  # triples of form_model, section_model, cde_model
        self.mongo_client = mongo_client
        self.testing = testing

    def generate(self):
        for cde_triple in self.cde_triples:
            sheet = self._create_sheet(cde_triple)

    def _create_sheet(self, cde_triple):
        sheet = self.workbook.add_worksheet()

        for patient in self._get_patients():
            self._add_patient_rows(patient, cde_triple, sheet)
        return sheet

    def _get_patients(self):
        from rdrf.registry.patients import Patient
        return Patient.objects.filter(working_groups__in=[self.working_groups],
                                      rdrf_registry__in=[self.registry_model])

    def _get_static_data(self, patient):
        # the demographic "fixed" data to appear in the row
        return {"id": patient.pk,
                "sex": patient.sex,
                "date_of_birth": patient.date_of_birth}

    def _get_longitudinal_data(self, patient, cde_triple):
        from rdrf.dynamic_data import DynamicDataWrapper
        wrapper = DynamicDataWrapper(patient)
        wrapper.testing = self.testing
        wrapper.client = self.mongo_client
        # get all snapshots for this patient
        history_collection = wrapper._get_collection(
            self.registry_model.code, "history")
        lower_bound, upper_bound = self._get_timestamp_bounds()

        patient_snapshots = history_collection.find({"django_id": patient.pk,
                                                     "registry_code": self.registry_model.code,
                                                     "django_model": "Patient",
                                                     "record_type": "snapshot"})

        # return a list of date pairs [ (timestamp1, value1), (timestamp2,
        # value2), ...]
        pairs = self._get_value_pairs(patient_snapshots, cde_triple)
        logger.debug("pairs = %s" % pairs)
        return pairs

    def _get_value_pairs(self, patient_snapshots, cde_triple):

        pairs = []
        form_model, section_model, cde_model = cde_triple
        snapshots = [ s for s in patient_snapshots]
        for snapshot in snapshots:
            timestamp = snapshot["timestamp"]
            patient_record = snapshot["record"]
            value = get_cde_value(form_model, section_model,
                                  cde_model, patient_record)
            pairs.append((timestamp, value))
        return pairs

    def _get_timestamp_bounds(self):
        dt_lower, dt_upper = self.time_window
        lower_bound = dt_lower
        upper_bound = dt_upper
        return (lower_bound, upper_bound)

    def _add_wide_row(self, patient, cde_triple, static_data, longitudinal_data):
        # id|sex|date_of_birth|diagnosis|etc|date1|cde value1|date2|cde value2|
        # ...
        pass

    def _add_long_rows(self, patient, cde_triple, static_data, longitudinal_data):
        # id|sex|date_of_birth|diagnosis|etc|date1|cde value1
        # id|sex|date_of_birth|diagnosis|etc|date2|cde value2
        # id|sex|date_of_birth|diagnosis|etc|date3|cde value3
        pass

    def _add_patient_rows(self, patient, cde_triple, sheet):
        # the non-varying part - should this be configured per varying cde
        # though?
        static_data = self._get_static_data(patient)
        longitudinal_data = self._get_longitudinal_data(patient, cde_triple)
        if self.report_format == SpreadSheetReportFormat.WIDE:
            self._add_wide_row(patient, cde_triple,
                               static_data, longitudinal_data)
        else:
            self._add_long_rows(patient, cde_triple,
                                static_data, longitudinal_data)
