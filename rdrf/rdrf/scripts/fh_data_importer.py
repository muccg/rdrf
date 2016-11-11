import django
django.setup()

from django.db import transaction
from rdrf.models import Registry
from rdrf.models import RegistryForm
from rdrf.models import Section
from rdrf.models import CommonDataElement
from rdrf.form_view import FormView
from django.test import RequestFactory

from registry.patients.models import Patient
from registry.groups.models import CustomUser


import openpyxl as xl
import os
import sys


class DataDictionary:
    FIELD_NUM_COLUMN = 1
    FORM_NAME_COLUMN = 2
    SECTION_NAME_COLUMN = 3
    CDE_NAME_COLUMN = 4
    PATIENT_ID_FIELDNUM = 1
    INDEX_FIELD_NUM = 29
    INDEX_VALUE = "index"
    RELATIVE_VALUE = "relative"


class ImporterError(Exception):
    pass


class FieldNumNotFound(ImporterError):
    pass


class FieldType:
    CDE = 1
    DEMOGRAPHICS = 2
    PEDIGREE_FORM = 3
    CONSENT = 4


DEMOGRAPHICS_TABLE = [
    # fieldnum(column for data), English, field_expression, converter func (if
    # any)
    (1, "Centre"),
    (2, "Family name", "family_name"),
    (3, "Given names", "given_names"),
    (4, "Maiden name", "maiden_name"),
    (5, "Hospital/Clinic ID", ""),
    (6, "Date of birth", "date_of_birth"),
    (7, "Country of birth", "country_of_birth"),
    (8, "Ethnic Origin", "ethnic_origin"),
    (9, "Sex", "gender"),
    (10, "Home Phone", "home_phone"),
    (11, "Mobile Phone", "mobile_phone"),
    (12, "Work Phone", "work_phone"),
    (14, "Email", "email"),
    (15, "Living status", "living_status"),
    (17, "Address", "Demographics/Address/Home/Address"),
    (18, "Suburb/Town", "Demographics/Address/Home/Suburb"),
    (19, "State", "Demographics/Address/Home/State"),
    (20, "Postcode", "Demographics/Address/Home/Postcode"),
    (21, "Country", "Demographic/Address/Home/Country")
]


class SpreadsheetImporter(object):
    # rewriting importer
    # as we need to link relatives to index patients
    # so we do two passes
    # also FH introduced form groups
    # we need to be aware of them

    def __init__(self, registry_model, import_spreadsheet_filepath, datadictionary_sheetname, datasheet_name):
        self.registry_model = registry_model
        self.import_spreadsheet_filepath = import_spreadsheet_filepath
        self.datadictionary_sheetname = datadictionary_sheetname
        self.datadictionary_sheet = None
        self.datasheet_name = datasheet_name
        self.data_sheet = None
        self.indexes = []
        self.relatives = []
        self.family_linkage_map = {}
        self.index_patient_map = {}
        self.field_map = {}
        self.id_map = {}
        self._load_workbook()
        self._load_datasheet()
        self._load_datadictionary_sheet()
        self._build_field_map()

    def _load_workbook(self):
        if not os.path.exists(self.import_spreadsheet_filepath):
            raise ImporterError("Spreadsheet file %s does not exist" %
                                self.import_spreadsheet_filepath)

        try:
            self.workbook = xl.load_workbook(self.import_spreadsheet_filepath)

        except Exception as ex:
            raise ImporterError("Could not load Import spreadsheet: %s",
                                ex)

    def _load_datadictionary_sheet(self):
        self.datadictionary_sheet = self.workbook.get_sheet_by_name(
            self.datadictionary_sheetname)

    def _load_datasheet(self):
        self.data_sheet = self.workbook.get_sheet_by_name(self.datasheet_name)

    def _get_value(self, sheet, row, column):
        return sheet.cell(row=row,
                          column=column).value

    def _build_field_map(self):
        print("building field map ..")
        # map RDRF "fields" to fieldnums in the spreadsheet
        d = {}
        d["patient_id"] = DataDictionary.PATIENT_ID_FIELDNUM

        sheet = self.datadictionary_sheet
        finished = False
        row_num = 3  # fields start here

        while not finished:
            field_num = self._get_value(sheet,
                                        row_num,
                                        DataDictionary.FIELD_NUM_COLUMN)

            if not field_num:
                finished = True
            else:
                form_name = self._get_value(sheet,
                                            row_num,
                                            DataDictionary.FORM_NAME_COLUMN)

                section_name = self._get_value(sheet,
                                               row_num,
                                               DataDictionary.SECTION_NAME_COLUMN)

                cde_name = self._get_value(sheet,
                                           row_num,
                                           DataDictionary.CDE_NAME_COLUMN)

                key = (form_name, section_name, cde_name)

                d[key] = field_num
                print("field map key %s = %s" % (key, field_num))

                row_num += 1
        return d

    def _get_field_num(self, key):
        if type(key) is tuple:
            form_model, section_model, cde_model = key
            form_name = form_model.name
            section_name = section_model.display_name
            cde_name = cde_model.name

            k = (form_name, section_name, cde_name)
            if k in self.field_map:
                return self.field_map[k]
            else:
                msg = "%s/%s/%s" % (form_name, section_name, cde_name)
                raise FieldNumNotFound(msg)
        else:
            # string key
            if key in self.field_map:
                return self.field_map[key]
            else:
                raise FieldNumNotFound(key)

    def run(self):
        print("beginning run")
        self._load_datasheet()
        row = 2  # data starts here

        # first find which rows are index patients, which relatives
        print("sorting indexes from relatives ...")
        scanned = False
        while not scanned:
            print("checking row %s" % row)
            if self._check_type(row, check_index=True):
                self.indexes.append(row)
                row += 1
            elif self._check_type(row, check_index=False):
                self.relatives.append(row)
                row += 1
            else:
                print("finished scanning")
                scanned = True

        # now begin processing for real
        self._create_indexes()
        self._create_relatives()

    def _get_column(self, field_num, row):
        return self.data_sheet.cell(row=row,
                                    column=int(field_num))

    def _check_type(self, row, check_index=True):
        index_cell = self._get_value(self.data_sheet,
                                     row,
                                     DataDictionary.INDEX_FIELD_NUM)

        if check_index:
            check_value = DataDictionary.INDEX_VALUE
        else:
            check_value = DataDictionary.RELATIVE_VALUE

        value = index_cell == check_value
        return value

    def _is_relative(self, row):
        value = self._get_column(
            DataDictionary.INDEX_FIELD_NUM, row) == DataDictionary.RELATIVE_VALUE
        print("checking row %s value =%s" % (row, value))
        if value:
            print("row %s in relative" % row)
        return value

    def _create_indexes(self):
        for row in self.indexes:
            index_patient = self._import_patient(row)
            external_id = self._get_external_id(row)
            self._update_id_map(external_id, index_patient.pk)

    def _update_id_map(self, external_id, rdrf_id):
        if external_id in self.id_map:
            raise ImportError("Dupe ID?")
        else:
            self.id_map[external_id] = rdrf_id

    def _create_relatives(self):
        for row in self.relatives:
            patient = self._create_minimal_patient(row)
            external_id = self._get_external_id(row)
            self._import_demographics_data(patient, row)
            for form_model in self.form_models:
                self._import_clinical_form(form_model, patient, row)

            self._update_id_map(external_id, patient.pk)

            index_patient = self._get_index_patient(row)
            self._add_relative(index_patient, patient)

    def _get_field(self, row, field):
        if type(field) is type(basestring):
            # demographics
            field_num = self._get_field_num(field)
            value = self._get_value(self.data_sheet,
                                    row,
                                    field_num)
            return value

    def _import_demographics_data(self, patient, row):
        for t in DEMOGRAPHICS_TABLE:
            updates = []
            has_converter = len(t) == 4
            field_num = t[0]
            field_expression = t[2]
            value = self._get_column(field_num, row)
            if has_converter:
                converter_name = t[3]
                converter_func = self._get_converter_func(converter_name)
                value = converter_func(value)
            updates.append((field_expression, value))

        patient.update_field_expressions(updates)

    def _import_patient(self, row):
        patient = Patient()
        self._import_demographics_data(patient, row)
        self._import_pedigree_data(patient, row)
        # ensure we import data into the correct context

        for context_model, form_model in self.get_forms_and_contexts():
            self._import_clinical_form(form_model, patient, context_model, row)

        return patient

    def _get_forms_and_contexts(self, patient_model):
        # get forms in fixed groups
        results = []
        for context_form_group in self.registry_model.context_form_groups:
            if context_form_group.is_default and context_form_group.type == "F":
                try:
                    context_model = RDRFContext.objects.get(object_id=patient_model.pk,
                                                            registry=self.registry_model,
                                                            context_form_group=context_form_group)
                except RDRFContext.DoesNotExist:
                    # should not happen as contexts for fixed groups created
                    # when patient craeted
                    pass

                except RDRFContext.MultipleObjectsReturned:
                    # eek
                    pass

                for form_model in context_form_group.form_models:
                    results.append((context_model, form_model))
        return results

    def _import_clinical_form(self, form_model, patient_model, context_model, row):
        field_updates = []
        for section_model in form_model.section_models:
            if not section_model.allow_multiple:
                # 1st data import sheet does not contain any multisections as
                # is 1 row per patient
                for cde_model in section_model.cde_models:
                    if self.included(form_model, section_model, cde_model):
                        field_num = self._get_field_num(
                            form_model, section_model, cde_model)
                        field_value = self._get_field_value(row, field_num)
                        field_expression = self._get_field_expression(
                            patient_model, form_model, section_model, cde_model)
                        field_updates.append((field_expression, field_value))

        patient_model.update_field_expressions(
            self.registry_model, field_updates)

    def cde_included(self, form_model, section_model, cde_model):
        model_tuple = (form_model, section_model, cde_model)
        return model_tuple in self.field_map

    def _get_field_expression(self, patient_model, form_model, section_model, cde_model):

        return expresssion

if __name__ == "__main__":
    registry_code = sys.argv[1]
    spreadsheet_file = sys.argv[2]
    dictionary_sheet_name = sys.argv[3]
    data_sheet_name = sys.argv[4]
    registry_model = Registry.objects.get(code=registry_code)
    spreadsheet_importer = SpreadsheetImporter(registry_model,
                                               spreadsheet_file,
                                               dictionary_sheet_name,
                                               data_sheet_name)
    spreadsheet_importer.run()
