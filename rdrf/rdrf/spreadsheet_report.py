from rdrf.utils import get_cde_value
import openpyxl as xl
import logging
import json
from collections import OrderedDict
from rdrf.utils import generalised_field_expression
from rdrf.dynamic_data import DynamicDataWrapper

logger = logging.getLogger("registry_log")


def default_time_window():
    from datetime import datetime, timedelta
    one_year = timedelta(days=365)
    today = datetime.now()
    one_year_ago = today - one_year
    return (one_year_ago, today)


class SpreadSheetReport(object):

    def __init__(self,
                 query_model,
                 testing=False):
        self.registry_model = query_model.registry
        self.projection_list = json.loads(query_model.projection)
        self.longitudinal_column_map = self._build_longitudinal_column_map()
        self.output_filename = "%s_report.xlsx" % registry_model.code
        self.work_book = xl.WorkBook()
        self.testing = testing
        self.current_sheet = None
        self.current_row = 1
        self.current_col = 1

    def _build_longitudinal_column_map(self):
        d = {}
        for cde_dict in self.projection_list:
            if cde_dict["longitudinal"]:
                form_name = cde_dict["formName"]
                section_code = cde_dict["sectionCode"]
                if (form_name, section_code) in d:
                    d[(form_name, section_code)].append(cde_dict["cdeCode"])
                else:
                    d[(form_name, section_code)] = [cde_dict["cdeCode"]]
        return d

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
                                                            value))

    def generate(self):
        config = json.loads(self.query_model.sql_query)
        static_sheets = config["static_sheets"]
        for static_sheet_dict in static_sheets:
            name = registry_model.code.upper() + static_sheet["name"]
            columns = static_sheet["columns"]
            self._create_static_sheet(name, columns)
        # these columns are always included prior
        universal_columns = config["universal_columns"]
        # to the longitudinal data
        for form_model in self.registry_model.forms:
            for section_model in form_model.section_models:
                if self._section_in_report(form_model, section_model):
                    self._create_longitudinal_section_sheet(
                        universal_columns, form_model, section_model)

    def _section_in_report(self, form_model, section_model):
        for cde_dict in self.projection_list:
            if form_model.name == cde_dict["formName"] and section_model.code == cde_dict["sectionCode"]:
                return True

    def _create_static_sheet(self, name, columns):
        self._create_sheet(name)
        self._write_header_row(columns)
        self._next_row()

        for patient in self._get_patients():
            self._write_row(patient, columns)
            self._next_row()

    def _write_row(self, patient, columns):
        for column in columns:
            value = evaluate_field_expression(
                self.registry_model, patient, column)
            self._write_cell(value)
            self._next_cell()

    def _create_longitudinal_section_sheet(self, form_model, section_model, universal_columns):
        sheet_name = self.registry_model.code.upper() + section_model.code
        self._create_sheet(sheet_name)
        self._write_longitudinal_header(
            universal_columns, form_model, section_model)
        self.next_row()
        for patient in self._get_patients():
            self._write_row(patient, universal_columns)
            self._write_longitudinal_row(patient, form_model, section_model)
            self.next_row()

    def _create_sheet(self, name):
        sheet = self.work_book.create_sheet()
        self.current_sheet = sheet
        self.current_row = 1
        self.current_col = 1

    def _write_header_row(self, columns):
        for column_name in columns:
            self._write_cell(column_name)
            self.next_cell()

    def _get_patients(self):
        from rdrf.registry.patients import Patient
        return Patient.objects.filter(working_groups__in=[self.working_groups],
                                      rdrf_registry__in=[self.registry_model]).order_by("id")

    def _write_longitudinal_header(self, universal_columns, form_model):
        pass

    def _write_longitudinal_row(self, patient, form_model, section_model):
        cde_codes = self._longitudinal_column_map.get(
            (form_model.name, section_model.code), [])
        for snapshot in self._get_snapshots(patient):
            timestamp = self._get_timestamp_from_snapshot(snapshot)
            values = []
            for cde_code in cde_codes:
                value = self._get_cde_value_from_snapshot(snapshot,
                                                          form_model.name,
                                                          section_model.code,
                                                          cde_code)
                values.append(value)
            self._write_cell(timestamp)
            self.next_cell()
            for value in values:
                self._write_cell(value)
                self.next_cell()

    @cached
    def _get_snapshots(self, patient_model):
        wrapper = DynamicDataWrapper(patient)
        wrapper.testing = self.testing
        wrapper.client = self.mongo_client
        history_collection = wrapper._get_collection(
            self.registry_model.code, "history")
        lower_bound, upper_bound = self._get_timestamp_bounds()

        patient_snapshots = history_collection.find({"django_id": patient.pk,
                                                     "registry_code": self.registry_model.code,
                                                     "django_model": "Patient",
                                                     "record_type": "snapshot"})
        return patient_snapshots

    def _get_timestamp_bounds(self):
        dt_lower, dt_upper = self.time_window
        lower_bound = dt_lower
        upper_bound = dt_upper
        return (lower_bound, upper_bound)
