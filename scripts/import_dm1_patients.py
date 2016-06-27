import django
django.setup()

import sys
import os
from django.db import transaction
from rdrf.models import Registry


class Columns:
    FIRST_NAME = 2
    FAMILY_NAME = 3


class Dm1Importer(object):
    COLS = {
        # from spreadsheet sample
        # NHI	First Name	Family Name	DOB	Date of consent	Genetic Test recd.	Diagnosis	Sex	Ethnicity	Postal address 1
        # Address 2	Address 3	Address 4	Pcode	Email	Home Ph	Mobile	Participants representative
        # Relationship to participant	Address	Email	Ph	<no value> Key

        1: "NHI",
        2: "First Name",
        3: "Family Name",
        4: "DOB",
        5: "Date of consent",
        6: "Genetic Test recd.",
        7: "Diagnosis",
        8: "Sex",
        9: "Ethnicity",
        10: "Postal Address 1",
        11: "Address 2",
        12: "Address 3",
        13: "Address 4",
        14: "Pcode",
        15: "Email",
        16: "Home Ph",
        17: "Mobile",
        18: "Participants Representative",
        19: "Relationship to Participant",
        20: "Address",
        21: ("Email", "repemail"),
        22: ("Ph", "repphone"),
        23: (None, None),
        24: ("Key", "repkey")

    }

    def __init__(self, registry_model, excel_filename):
        self.excel_filename = excel_filename
        self.registry_model = registry_model
        self.errors = []
        self.num_patients_created = 0
        self.current_row = 2
        self.current_patient = None

    def run(self):
        while self.current_row is not None:
            row = {}
            for column_index in range(1, 24):
                field_name = self.COLS[column_index]
                row[column_index] = self._get_cell(current_row, column_index)

            if self._is_blank_row(row):
                self._display_summary()
                self.current_row = None
            else:
                self._process_row(row)
                self.current_row += 1

    def _is_blank_row(self, row_dict):
        return all([row_dict[Columns.FIRST_NAME] == "",
                    row_dict[Columns.FAMILY_NAME] == ""])

    def _display_summary(self):
        print "%s patients imported" % self.num_patients_created
        print "Number of errors: %s" % len(self.errors)
        for error_dict in self.errors:
            self._print_error(error_dict)

    def _print_error(error_dict):
        print "Error importing row %s: %s" % (error_dict["row_num"], error_dict["error_message"])

    def _process_row(self, row_dict):
        self.current_patient = self._create_minimal_patient(row_dict)
        self._update_consents(row_dict)
        self._update_demographics(row_dict)
        self._create_address(row_dict)
        self._update_clinical_data(row_dict)


if __name__ == '__main__':
    excel_filename = sys.argv[1]
    if not os.path.exists(excel_filename):
        print "Excel file does not exist"
        sys.exit(1)

    registry_code = "DM1"
    try:
        registry_model = Registry.objects.get(code=registry_code)
    except Registry.DoesNotExist:
        print "DM1 has not been imported"
        sys.exit(1)

    try:
        with transaction.atomic():
            dm1_importer = Dm1Importer(registry_model, excel_filename)
            dm1_importer.run()
            sys.exit(0)

    except Exception, ex:
        print "Error running import (will rollback): %s" % ex
        sys.exit(1)
