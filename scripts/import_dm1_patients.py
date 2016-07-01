import django
django.setup()

import sys
import os
import re
from datetime import datetime

from django.db import transaction
from rdrf.models import Registry
from registry.groups.models import WorkingGroup
from registry.patients.models import Patient
from openpyxl import load_workbook


class Columns:
    GIVEN_NAMES = 2
    FAMILY_NAME = 3
    DOB = 4
    SEX = 8


class ProcessingError(Exception):

    def __init__(self, row_number, column_label, patient_model, message):
        super(ProcessingError, self).__init__(message)
        self.row_number = row_number
        self.column_label = column_label
        self.patient_model = patient_model

    def __unicode__(self):
        return "Error row %s column %s patient %s: %s" % (self.row_number,
                                                          self.column_label,
                                                          self.patient_model,
                                                          self.message)


class Dm1Importer(object):
    MINIMAL_FIELDS = [Columns.GIVEN_NAMES,
                      Columns.FAMILY_NAME, Columns.DOB, Columns.SEX]
    COLS = {
        # from spreadsheet sample
        # NHI	First Name	Family Name	DOB	Date of consent	Genetic Test recd.	Diagnosis	Sex	Ethnicity	Postal address 1
        # Address 2	Address 3	Address 4	Pcode	Email	Home Ph	Mobile	Participants representative
        # Relationship to participant	Address	Email	Ph	<no value> Key

        # column index --> (column label, generalised field expression/set_function name, convert function name (if any))
        # if second of pair is None - we have a special case -
        1: ("NHI", "umrn"),
        2: ("First Name", "given_names"),
        3: ("Family Name", "family_name"),
        4: ("DOB", "date_of_birth"),
        5: ("Date of consent", "set_consent"),
        6: ("Genetic Test recd.", "ClinicalData/DM1GeneticTestDetails/GeneticTestResultsAvailable", "convert_genetic_test_received"),
        7: ("Diagnosis", "ClinicalData/DM1Status/DM1Condition", "convert_dm1condition"),
        8: ("Sex", "sex"),
        9: ("Ethnicity", "set_ethnic_origin"),
        # Address spans multiple columns - special case
        10: ("Postal Address 1", None),
        11: ("Address 2", None),
        12: ("Address 3", None),
        13: ("Address 4", None),
        14: ("Pcode", None),
        15: ("Email", "email"),
        16: ("Home Ph", "home_phone"),
        17: ("Mobile", "mobile_phone"),
        # Special case also
        18: ("Participants Representative", None),
        19: ("Relationship to Participant", None),
        20: ("Address", None),
        21: ("Email", None),
        22: ("Ph", None),
        23: (None, None),
        24: ("Key", None)

    }

    def __init__(self, registry_model, excel_filename):
        self.excel_filename = excel_filename
        self.workbook = load_workbook(self.excel_filename)
        self.sheet = self.workbook.worksheets[0]

        self.registry_model = registry_model
        self.working_group = WorkingGroup.objects.get(registry=self.registry_model,
                                                      name="New Zealand")

        self.errors = []
        self.num_patients_created = 0
        self.current_row = 2  # 1 based
        self.current_patient = None
        self.log_name = "IMPORTER "  # so we can grep
        self.log_prefix = "INIT"

    def log(self, msg):
        print "%s %s: %s" % (self.log_name, self.log_prefix, msg)

    def _get_cell(self, current_row, column_index):
        value = self.sheet.cell(row=current_row, column=column_index).value
        self.log("cell row %s col %s = %s" %
                 (current_row, column_index, value))
        return value

    def run(self):
        while self.current_row is not None:
            row = {}
            for column_index in range(1, 24):
                row[column_index] = self._get_cell(
                    self.current_row, column_index)

            if self._is_blank_row(row):
                self.log_prefix = "Finished"
                self._display_summary()
                self.current_row = None
            else:
                self.log(
                    "************************************************************************")
                self._process_row(row)
                self.log(
                    "************************************************************************")
                self.current_row += 1

    def _is_blank_row(self, row_dict):
        return all(map(lambda index: row_dict[index] is None, self.MINIMAL_FIELDS))

    def _display_summary(self):
        self.log("%s patients imported" % self.num_patients_created)
        self.log("Number of errors: %s" % len(self.errors))
        for error_dict in self.errors:
            self._print_error(error_dict)

    def _print_error(self, error):
        self.log("ERROR: %s" % error)
        

    def _process_row(self, row_dict):
        self.log_prefix = "Row %s" % self.current_row
        self.log("starting to process")
        self.current_patient = self._create_minimal_patient(row_dict)
        self.log("created minimal patient %s" % self.current_patient)
        for i in self.COLS:
            if i not in self.MINIMAL_FIELDS and self.COLS[i][1] is not None:
                column_name = self.COLS[i][0]
                self.log("Updating from column %s" % column_name)
                try:
                    self._update_field(i, row_dict)
                except Exception, ex:
                    self.errors.append(ProcessingError(self.current_row,
                                                       column_name,
                                                       self.current_patient,
                                                       ex.message))

        self._set_address_fields()
        self._set_parent_guardian_fields(row_dict)
        self.log("Finished row")

    def _set_address_fields(self):
        self.log("address fields - to do")

    def set_ethnic_origin(self, raw_value):
        mapping = {"nz european": "new zealand european",
                   "nz european/maori": "nz european / maori"}
        
        v = raw_value.lower().strip()
        if not v:
            self.current_patient.ethnic_origin = None
            self.current_patient.save()
        
        v = mapping.get(v, v)
        
        other = "Other Ethnicity"
        x = other
        for eo, _ in Patient.ETHNIC_ORIGIN:
            if eo.lower() == v:
                x = eo
                break
        self.current_patient.ethnic_origin = x
        self.current_patient.save()

    def _set_parent_guardian_fields(self, row_dict):
        print "set parent guardian fields - to do"

    def _update_field(self, column_index, row_dict):
        column_info = self.COLS[column_index]
        converter = None
        if len(column_info) == 2:
            column_label, field_expression = column_info
        else:
            column_label, field_expression, converter_name = column_info
            converter = getattr(self, converter_name)

        self.log("Updating %s from %s" % (field_expression, column_label))

        if field_expression.startswith("set_"):
            # custom set_ function
            self.log("running set_function %s" % field_expression)
            func = getattr(self, field_expression)
            value = row_dict[column_index]
            self.log("raw_value = %s" % value)
            if converter is not None:
                self.log("raw_value will be converted")

                self.log("value before conversion = %s" % value)
                converted = converter(value)
                self.log("value after conversion = %s" % converted)

                func(converted)
            else:
                if value is None:
                    self.log("value is None - won't set")
                else:
                    self.log("running %s on %s" % (field_expression, value))
                    func(value)

        else:
            # generalised field expression
            self.log("updating %s" % field_expression)
            value = row_dict[column_index]
            if converter is not None:
                value = converter(value)

            self._execute_field_expression(field_expression, value)

    def _execute_field_expression(self, field_expression, value):
        print "setting %s --> %s" % (field_expression, value)
        self.current_patient.evaluate_field_expression(self.registry_model,
                                                       field_expression,
                                                       value=value)

    def set_consent(self, consent_date_string):
        # D/M/YYYY
        consent_date_string = consent_date_string.strip()
        if not consent_date_string:
            return
        pattern = re.compile(r"^(\d\d?)\/(\d\d?)\/(\d\d\d\d)$")

        m = pattern.match(consent_date_string)
        if not m:
            return

        try:
            day, month, year  = map(int,m.groups())
            consent_date = datetime.date(year, month, day)
        except:
            return

        #check consents: dm1consentsec01 (c2) and dm1consentsec02 (c1 and c2)
        self.execute_field_expression("Consents/dm1consentsec01/c2/answer", True)
        self.execute_field_expression("Consents/dm1consentsec01/c2/first_save", consent_date)
        self.execute_field_expression("Consents/dm1consentsec01/c2/last-update", consent_date)

        self.execute_field_expression("Consents/dm1consentsec02/c1/answer", True)
        self.execute_field_expression("Consents/dm1consentsec02/c1/first_save", consent_date)
        self.execute_field_expression("Consents/dm1consentsec02/c1/last-update", consent_date)

        self.execute_field_expression("Consents/dm1consentsec02/c2/answer", True)
        self.execute_field_expression("Consents/dm1consentsec02/c2/first_save", consent_date)
        self.execute_field_expression("Consents/dm1consentsec02/c2/last-update", consent_date)

        

    def _get_field_value(self, our_field_name, row_dict):
        value = None
        for index in self.COLS:
            column_info = self.COLS[index]
            if len(column_info) == 2:
                column_label, our_expression = self.COLS[index]
            else:
                column_label, our_expression, _ = self.COLS[index]

            if our_field_name == our_expression:
                value = row_dict[index]
                break
        print "field %s = %s" % (our_field_name, value)
        return value

    def convert_dm1condition(self, value):
        # NB the RDRF PVG range values
        v = value.lower().strip()
        mapping = {"myotonic dystrophy": "DM1ConditionDM1",
                   "proximal myotonic myopathy promm": "DM1ConditionDM2"}

        return mapping[v]

    def _create_minimal_patient(self, row_dict):
        self.log("creating patient ...")
        p = Patient()
        p.given_names = self._get_field_value("given_names", row_dict)
        p.family_name = self._get_field_value("family_name", row_dict)
        p.sex = self._convert_sex(self._get_field_value("sex", row_dict))
        p.date_of_birth = self._convert_date_of_birth(self._get_field_value("date_of_birth",
                                                                            row_dict))

        p.consent = True
        p.active = True

        p.save()
        self.log("saved minimal fields for %s" % p)

        p.rdrf_registry = [self.registry_model]
        p.working_groups = [self.working_group]
        p.save()
        self.log("assigned to %s and %s" % (self.registry_model,
                                            self.working_group))

        self.num_patients_created += 1

        return p

    def _convert_date_of_birth(self, dob):
        return dob

    def _convert_sex(self, raw_sex):
        mapping = {
            "M" : 1,
            "F" : 2
        }

        return mapping.get(raw_sex, None)

    def convert_genetic_test_received(self, raw_value):
        mapping = {
            "yes": "YesNoUnknownYes",
            "no":  "YesNoUnknownNo",
            "pending": "YesNoUnknownUnknown", # !! - this was requested in RDR-1333 ...
            "family member +ve test": "YesNoUnknownUnknown" # ditto

        }

        if not raw_value:
            return None
        
        return mapping.get(raw_value.lower().strip(), None)


if __name__ == '__main__':
    excel_filename = sys.argv[1]
    if not os.path.exists(excel_filename):
        print "Excel file does not exist"
        sys.exit(1)

    registry_code = "DM1"
    try:
        registry_model = Registry.objects.get(code=registry_code)
    except Registry.DoesNotExist:
        print "DM1 registry does not exist on the site - nothing imported"
        sys.exit(1)

    try:
        with transaction.atomic():
            dm1_importer = Dm1Importer(registry_model, excel_filename)
            dm1_importer.run()
            if len(dm1_importer.errors) > 0:
                raise Exception("processing errors occurred")

            print "run successful - NO ROLLBACK!"

    except Exception, ex:
        print "Error running import (will rollback): %s" % ex
        sys.exit(1)
