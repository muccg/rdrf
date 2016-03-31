from rdrf.utils import get_cde_value
import openpyxl as xl
import logging
from collections import OrderedDict

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
        self.work_book = xl.WorkBook()
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
        self.current_sheet = None
        self.current_row = 1
        self.current_col = 1

    def _move_right(self):
        self.current_col += 1

    def _move_down(self):
        self.current_row += 1

    def _move_beginning_row(self):
        self.current_col = 1

    def _move_next_row(self):
        self._move_down()
        self._move_beginning_row()

    def _move_reset(self):
        self.current_row = 1
        self.current_col = 1

    def _write_cell(self, value):
        # write value at current position
        cell = self.current_sheet.cell(
            row=self.current_row, column=self.current_col)
        cell.value = value
        logger.debug("cell updated: row %s col %s -> %s" % (self.current_row,
                                              self.current_col,
                                              value)

    def generate(self):
        for cde_triple in self.cde_triples:
            self._create_sheet(cde_triple)

    def _create_sheet(self, cde_triple):
        sheet_name=self._get_sheet_name(cde_triple)
        sheet=self.work_book.create_sheet()
        self.current_sheet=sheet

        for patient in self._get_patients():
            self._add_patient_rows(patient, cde_triple)

    def _get_sheet_name(self, cde_triple):
        form_model, section_model, cde_model=cde_triple
        name="%s %s %s" % (form_model.name[:3],
                             section_model.code[:3],
                             cde_model.name)
        return name.upper()

    def _get_patients(self):
        from rdrf.registry.patients import Patient
        return Patient.objects.filter(working_groups__in=[self.working_groups],
                                      rdrf_registry__in=[self.registry_model])

    def _get_static_data(self, patient):
        # the demographic "fixed" data to appear in the row
        d=OrderedDict()
        d["id"]=patient.pk
        d["sex"]=patient.sex
        d["dob"]=patient.date_of_birth
        return d


    def _get_longitudinal_data(self, patient, cde_triple):
        from rdrf.dynamic_data import DynamicDataWrapper
        wrapper=DynamicDataWrapper(patient)
        wrapper.testing=self.testing
        wrapper.client=self.mongo_client
        # get all snapshots for this patient
        history_collection=wrapper._get_collection(
            self.registry_model.code, "history")
        lower_bound, upper_bound=self._get_timestamp_bounds()

        patient_snapshots=history_collection.find({"django_id": patient.pk,
                                                     "registry_code": self.registry_model.code,
                                                     "django_model": "Patient",
                                                     "record_type": "snapshot"})

        # return a list of date pairs [ (timestamp1, value1), (timestamp2,
        # value2), ...]
        pairs=self._get_value_pairs(patient_snapshots, cde_triple)
        logger.debug("pairs = %s" % pairs)
        return pairs

    def _get_value_pairs(self, patient_snapshots, cde_triple):
        pairs=[]
        form_model, section_model, cde_model=cde_triple
        snapshots=[s for s in patient_snapshots]
        logger.debug("snapshots = %s" % snapshots)
        for snapshot in snapshots:
            timestamp=snapshot["timestamp"]
            patient_record=snapshot["record"]
            value=get_cde_value(form_model, section_model,
                                  cde_model, patient_record)
            pairs.append((timestamp, value))
        return pairs

    def _get_timestamp_bounds(self):
        dt_lower, dt_upper=self.time_window
        lower_bound=dt_lower
        upper_bound=dt_upper
        return (lower_bound, upper_bound)

    def _add_wide_row(self, patient, cde_triple, static_data, longitudinal_data):
        # id|sex|date_of_birth|diagnosis|etc|date1|cde value1|date2|cde value2|
        # ...
        self._write_static_data(patient, static_data)
        self._write_longitudinal_wide(longitudinal_data)

    def _write_static_data(self, patient, static_data):
        for field in static_data:
            value=static_data[field]
            self._write_cell(value)
            self._move_right()

    def _write_longitudinal_wide(self, longitudinal_data):
        for timestamp, field_value in longitudinal_data:
            self._write_cell(timestamp)
            self._move_right()
            self._write_cell(field_value)

    def _add_long_rows(self, patient, cde_triple, static_data, longitudinal_data):
        # id|sex|date_of_birth|diagnosis|etc|date1|cde value1
        # id|sex|date_of_birth|diagnosis|etc|date2|cde value2
        # id|sex|date_of_birth|diagnosis|etc|date3|cde value3
        pass

    def _add_patient_rows(self, patient, cde_triple):
        # the non-varying part - should this be configured per varying cde
        # though?
        static_data=self._get_static_data(patient)
        longitudinal_data=self._get_longitudinal_data(patient, cde_triple)
        if self.report_format == SpreadSheetReportFormat.WIDE:
            self._add_wide_row(patient, cde_triple,
                               static_data, longitudinal_data)
            self._move_next_row()
        else:
            self._add_long_rows(patient, cde_triple,
                                static_data, longitudinal_data)
