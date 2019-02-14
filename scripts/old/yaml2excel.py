#!/usr/bin/env python
import argparse
import yaml
import xlsxwriter as xl
from xlsxwriter.utility import xl_rowcol_to_cell as get_cell


def _l(s):
    return sorted(s.split("/"))


def _s(l):
    return "\n".join(l)


TEXT = "TEXT"
DECIMAL = "DECIMAL"
DATE = "DATE(dd/mm/yyyy)"
INTEGER = "INTEGER"
CALC = "CALCULATED"
FILE = "FILE"
RANGE = "DROPDOWN"
BOOL = _l("True/False")
SEXES = _l("M/F/I")
COUNTRIES = _l("AU/NZ")
STATES = _l("WA/NSW/NT/SA/VIC/TAS/QLD/ACT")
# not sure if we need these
# Name = Taranaki   CODE = NZ-TKI
# Name = Chatham Islands Territory   CODE = NZ-CIT
# Name = Nelson City   CODE = NZ-NSN
# Name = Bay of Plenty   CODE = NZ-BOP
# Name = West Coast   CODE = NZ-WTC
# Name = Gisborne District   CODE = NZ-GIS
# Name = Canterbury   CODE = NZ-CAN
# Name = Marlborough District   CODE = NZ-MBH
# Name = Hawke's Bay   CODE = NZ-HKB
# Name = Wellington   CODE = NZ-WGN
# Name = Southland   CODE = NZ-STL
# Name = Manawatu-Wanganui   CODE = NZ-MWT
# Name = North Island   CODE = NZ-N
# Name = Waikato   CODE = NZ-WKO
# Name = Otago   CODE = NZ-OTA
# Name = South Island   CODE = NZ-S
# Name = Tasman District   CODE = NZ-TAS
# Name = Auckland   CODE = NZ-AUK
# Name = Northland   CODE = NZ-NTL

NZ_STATES = _l("NZ-TKI/NZ-CIT/NZ-NSN/NZ-BOP/NZ-WTC/NZ-GIS/NZ-CAN/NZ-MBH/NZ-HKB/NZ-WGN/NZ-STL/NZ-MWT/NZ-N/NZ-WKO/NZ-OTA/NZ-S/NZ-TAS/NZ-AUK/NZ-NTL")

STATES.extend(NZ_STATES)

ETHNICITIES = sorted(["Aboriginal",
                      "Person from Torres Strait Islands",
                      "Black African/African American",
                      "Caucasian/European",
                      "Chinese",
                      "Indian",
                      "Maori",
                      "Aboriginal",
                      "Middle eastern",
                      "Person from the Pacific Islands",
                      "Other Asian",
                      "Other",
                      "Decline to Answer"])


class SpreadSheetCreator(object):
    def __init__(self, registry_dict, output_filename, nrows=300, excludes=[]):
        self.registry_dict = registry_dict
        self.output_filename = output_filename
        self.current_column = 1
        self.excludes = excludes
        self.nrows = nrows

    def create(self):
        self.workbook = xl.Workbook(self.output_filename, {"default_date_format": "dd/mm/yyyy"})
        self.sheet = self.workbook.add_worksheet()
        self._create_demographic_fields()
        self._create_registry_specific_fields()
        self.workbook.close()

    def _patient_demographics_spec(self):
        return [("Family Name", TEXT),
                ("Given Names", TEXT),
                ("Maiden Name", TEXT),
                # DM1 consents - will need to add FH consents
                ("Consent given to store data only while individual is living", BOOL),
                ("Consent given to store data for the duration of the registry", BOOL),
                ("Consent provided by Parent/Guardian only while individual is living", BOOL),
                ("Consent provided by Parent/Guardian for the duration of the registry", BOOL),
                ("Consent to allow for clinical trials given", BOOL),
                ("Consent to be sent information given", BOOL),
                ("Centre", TEXT),
                ("HOSPITAL/Clinic ID", TEXT),
                ("DOB", DATE),
                ("Place of Birth", TEXT),
                ("Country of Birth", TEXT),
                ("Ethnic Origin", ETHNICITIES),
                ("Sex", SEXES),
                ("Home Phone", TEXT),
                ("Mobile Phone", TEXT),
                ("Work Phone", TEXT),
                ("Email", TEXT),
                ("Address", TEXT),
                ("Suburb/Town", TEXT),
                ("State", STATES),
                ("Country", COUNTRIES)]

    def _h(self, coord, text):
        header_format = self.workbook.add_format({'border': 1,
                                                  'bg_color': '#C6EFCE',
                                                  'bold': True,
                                                  'text_wrap': True,
                                                  'valign': 'vcenter',
                                                  'indent': 1})
        self.sheet.write(coord, text, header_format)

    def _create_demographic_fields(self):
        for field_name, field_info in self._patient_demographics_spec():
            self._write_header(self.current_column, field_name)
            self._write_info(self.current_column, field_info)
            self._apply_validation(self.current_column, field_info)
            self.current_column += 1

    def _apply_validation(self, column, datatype, values=None):
        if isinstance(datatype, list):
            values = datatype
            datatype = RANGE

        if datatype in [TEXT, FILE, CALC]:
            return
        elif datatype == INTEGER:
            validation = {
                "validate": "integer",
                "criteria": 'between',
                "minimum": 0,
                "maximum": 1000000}
        elif datatype == DATE:
            validation = {"validate": 'date', 'input_title': 'Enter a date dd/mm/yyyy'}
        elif datatype == DECIMAL:
            validation = {
                "validate": 'decimal',
                'input_title': 'Enter a decimal',
                'criteria': 'between',
                'minimum': -1000000.00,
                "maximum": 1000000.00}
        elif datatype == BOOL:
            validation = {"validate": 'list', 'source': ['True', 'False']}
        elif datatype == RANGE:
            if values is not None:
                if "---" not in values:
                    values.insert(0, '---')
                validation = {"validate": 'list', 'source': values}
            else:
                return

        else:
            return

        start_cell = get_cell(2, column)
        end_cell = get_cell(self.nrows + 2, column)
        applicable_cells = "%s:%s" % (start_cell, end_cell)
        print("applying validation %s to column %s" % (validation, column))
        self.sheet.data_validation(applicable_cells, validation)

    def _get_type(self, cde_dict):
        print("getting type for cde %s" % cde_dict)
        datatype = cde_dict['datatype'].lower().strip()
        if datatype in ['string', 'text']:
            return TEXT
        elif datatype in ['bool', 'boolean']:
            return BOOL
        elif datatype in ['integer']:
            return INTEGER
        elif datatype in ['float', 'decimal', 'numeric']:
            return DECIMAL
        elif datatype in ['calculated', 'calculation']:
            return CALC
        elif cde_dict['calculation']:
            return CALC
        elif datatype in ['date', 'datetime']:
            return DATE
        elif datatype == 'file':
            return FILE
        elif datatype in ["range"]:
            return RANGE
        elif cde_dict["pv_group"]:
            return RANGE
        else:
            raise Exception("Unknown datatype for %s: %s" % (cde_dict, datatype))

    def _get_range(self, cde_dict):
        pv_group = cde_dict['pv_group']
        return "\n".join(self._get_values(pv_group))

    def _get_values(self, pv_group):
        for group_dict in self.registry_dict['pvgs']:
            if pv_group == group_dict['code']:
                return sorted([v['value'] for v in group_dict['values']])
        raise Exception("Could get values for group %s" % pv_group)

    def _write_header(self, column, text):
        cell = get_cell(0, column)
        self._h(cell, text)

    def _write_info(self, column, text):
        if isinstance(text, list):
            text = _s(text)

        cell = get_cell(1, column)
        self.sheet.write(cell, text)

    def _get_cde_dict(self, code):
        for cde_dict in self.registry_dict['cdes']:
            if cde_dict['code'] == code:
                return cde_dict

    def _create_registry_specific_fields(self):
        for form_dict in self.registry_dict["forms"]:
            if form_dict['name'] in self.excludes:
                continue
            print("Adding fields for form %s" % form_dict['name'])
            for section_dict in form_dict["sections"]:
                if section_dict['code'] in self.excludes:
                    continue
                for cde_code in section_dict["elements"]:
                    if cde_code in self.excludes:
                        continue
                    cde_dict = self._get_cde_dict(cde_code)
                    if cde_dict is None:
                        raise Exception("cde is missing: %s" % cde_code)
                    field_header = "\n".join(
                        [form_dict['name'], section_dict['display_name'], cde_dict['name']])
                    datatype = self._get_type(cde_dict)
                    if datatype == RANGE:
                        values = self._get_values(cde_dict['pv_group'])
                        field_info = "\n".join([RANGE + ":"] + values)
                    else:
                        field_info = datatype

                    self._write_header(self.current_column, field_header)
                    self._write_info(self.current_column, field_info)
                    if datatype == RANGE:
                        self._apply_validation(self.current_column, datatype, values=values)
                    else:
                        self._apply_validation(self.current_column, datatype)
                    self.current_column += 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--yaml_file", "-y", required=True, dest='yaml_file')
    parser.add_argument("--output", "-o", required=True, dest='output_file')
    parser.add_argument("--exclude", "-e", dest='exclude', default="")
    parser.add_argument("--rows", "-r", type=int, dest='nrows', default=300)

    args = parser.parse_args()
    excludes = args.exclude.split(",")
    print("excludes = %s" % excludes)
    with open(args.yaml_file) as f:
        data = yaml.load(f)
    spreadsheet = SpreadSheetCreator(data, args.output_file, args.nrows, excludes=excludes)
    spreadsheet.create()
