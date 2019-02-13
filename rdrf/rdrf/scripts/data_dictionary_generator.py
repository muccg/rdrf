# encoding: utf-8
import yaml
import sys
from string import strip
import codecs


def decode(l):
    return map(lambda s: s.decode('utf-8'), l)


RANGE_DELIMITER = "|"
# COUNTRIES = decode(["Afghanistan", "Åland Islands", "Albania", "Algeria", "American Samoa", "Andorra", "Angola", "Anguilla", "Antarctica", "Antigua and Barbuda", "Argentina", "Armenia", "Aruba", "Australia", "Austria", "Azerbaijan", "Bahamas", "Bahrain", "Bangladesh", "Barbados", "Belarus", "Belgium", "Belize", "Benin", "Bermuda", "Bhutan", "Bolivia, Plurinational State of", "Bonaire, Sint Eustatius and Saba", "Bosnia and Herzegovina", "Botswana", "Bouvet Island", "Brazil", "British Indian Ocean Territory", "Brunei Darussalam", "Bulgaria", "Burkina Faso", "Burundi", "Cambodia", "Cameroon", "Canada", "Cape Verde", "Cayman Islands", "Central African Republic", "Chad", "Chile", "China", "Christmas Island", "Cocos (Keeling) Islands", "Colombia", "Comoros", "Congo", "Congo, The Democratic Republic of the", "Cook Islands", "Costa Rica", "Côte d'Ivoire", "Croatia", "Cuba", "Curaçao", "Cyprus", "Czech Republic", "Denmark", "Djibouti", "Dominica", "Dominican Republic", "Ecuador", "Egypt", "El Salvador", "Equatorial Guinea", "Eritrea", "Estonia", "Ethiopia", "Falkland Islands (Malvinas)", "Faroe Islands", "Fiji", "Finland", "France", "French Guiana", "French Polynesia", "French Southern Territories", "Gabon", "Gambia", "Georgia", "Germany", "Ghana", "Gibraltar", "Greece", "Greenland", "Grenada", "Guadeloupe", "Guam", "Guatemala", "Guernsey", "Guinea", "Guinea-Bissau", "Guyana", "Haiti", "Heard Island and McDonald Islands", "Holy See (Vatican City State)", "Honduras", "Hong Kong", "Hungary", "Iceland", "India", "Indonesia", "Iran, Islamic Republic of", "Iraq", "Ireland", "Isle of Man", "Israel", "Italy", "Jamaica", "Japan", "Jersey", "Jordan", "Kazakhstan", "Kenya", "Kiribati", "Korea, Democratic People's Republic of", "Korea, Republic of", "Kuwait", "Kyrgyzstan", "Lao People's Democratic Republic", "Latvia", "Lebanon", "Lesotho", "Liberia", "Libya", "Liechtenstein", "Lithuania", "Luxembourg",
#  "Macao", "Macedonia, Republic of", "Madagascar", "Malawi", "Malaysia", "Maldives", "Mali", "Malta", "Marshall Islands", "Martinique", "Mauritania", "Mauritius", "Mayotte", "Mexico", "Micronesia, Federated States of", "Moldova, Republic of", "Monaco", "Mongolia", "Montenegro", "Montserrat", "Morocco", "Mozambique", "Myanmar", "Namibia", "Nauru", "Nepal", "Netherlands", "New Caledonia", "New Zealand", "Nicaragua", "Niger", "Nigeria", "Niue", "Norfolk Island", "Northern Mariana Islands", "Norway", "Oman", "Pakistan", "Palau", "Palestine, State of", "Panama", "Papua New Guinea", "Paraguay", "Peru", "Philippines", "Pitcairn", "Poland", "Portugal", "Puerto Rico", "Qatar", "Réunion", "Romania", "Russian Federation", "Rwanda", "Saint Barthélemy", "Saint Helena, Ascension and Tristan da Cunha", "Saint Kitts and Nevis", "Saint Lucia", "Saint Martin (French part)", "Saint Pierre and Miquelon", "Saint Vincent and the Grenadines", "Samoa", "San Marino", "Sao Tome and Principe", "Saudi Arabia", "Senegal", "Serbia", "Seychelles", "Sierra Leone", "Singapore", "Sint Maarten (Dutch part)", "Slovakia", "Slovenia", "Solomon Islands", "Somalia", "South Africa", "South Georgia and the South Sandwich Islands", "Spain", "Sri Lanka", "Sudan", "Suriname", "South Sudan", "Svalbard and Jan Mayen", "Swaziland", "Sweden", "Switzerland", "Syrian Arab Republic", "Taiwan, Province of China", "Tajikistan", "Tanzania, United Republic of", "Thailand", "Timor-Leste", "Togo", "Tokelau", "Tonga", "Trinidad and Tobago", "Tunisia", "Turkey", "Turkmenistan", "Turks and Caicos Islands", "Tuvalu", "Uganda", "Ukraine", "United Arab Emirates", "United Kingdom", "United States", "United States Minor Outlying Islands", "Uruguay", "Uzbekistan", "Vanuatu", "Venezuela, Bolivarian Republic of", "Viet Nam", "Virgin Islands, British", "Virgin Islands, U.S.", "Wallis and Futuna", "Western Sahara", "Yemen", "Zambia", "Zimbabwe"])

COUNTRIES = []


ETHNICITIES = [
    "New Zealand European",
    "Australian",
    "Other Caucasian/European",
    "Aboriginal",
    "Person from the Torres Strait Islands",
    "Maori",
    "NZ European / Maori",
    "Samoan",
    "Cook Islands Maori",
    "Tongan",
    "Niuean",
    "Tokelauan",
    "Fijian",
    "Other Pacific Peoples",
    "Southeast Asian",
    "Chinese",
    "Indian",
    "Other Asian",
    "Middle Eastern",
    "Latin American",
    "Black African/African American",
    "Other Ethnicity",
    "Decline to Answer"]

SEXES = ["Male", "Female", "Indeterminate"]

LIVING_STATUSES = ["Living", "Deceased"]
AUS_STATES = ["ACT", "NSW", "NT", "QLD", "SA", "TAS", "VIC", "WA"]
BOOLEAN = ["True", "False"]


class DemographicForm:
    SECTION_REGISTRY = "Registry"
    SECTION_PATIENT_DETAILS = "Patients Personal Details"
    HOME_ADDRESS = "Home Address"
    PEDIGREE = "Pedigree"


class DemographicField(object):

    def __init__(
            self,
            section,
            name,
            datatype="STRING",
            members=[],
            validation="",
            required=False):
        self.name = name
        self.section = section
        self._members = members
        self.validation = validation
        self.datatype = datatype
        self.required = str(required)

        if self.datatype == "DATE":
            self.validation = "dd/mm/yyyy"

    @property
    def members(self):
        if self.datatype == "RANGE":
            return RANGE_DELIMITER.join(decode(self._members))
        return ""


class CDEWrapper(object):

    def __init__(self, data, cde_dict):
        self.data = data
        self.cde_dict = cde_dict

    @property
    def name(self):
        return self.cde_dict["name"]

    @property
    def required(self):
        return str(self.cde_dict["is_required"])

    @property
    def datatype(self):
        return self.cde_dict["datatype"].strip().upper()

    @property
    def members(self):
        if self.datatype == "RANGE":
            return RANGE_DELIMITER.join(self._get_allowed_values())
        else:
            return ""

    @property
    def validation(self):
        vals = []
        if self.datatype == "STRING":
            if self.cde_dict["max_length"]:
                vals.append("Length <= %s" % self.cde_dict["max_length"])
            if self.cde_dict["pattern"]:
                vals.append("Must conform to regular expression %s" %
                            self.cde_dict["pattern"])
        elif self.datatype == "INTEGER":
            if self.cde_dict["min_value"]:
                vals.append("Minimum value = %s" % self.cde_dict["min_value"])
            if self.cde_dict["max_value"]:
                vals.append("Maximum value = %s" % self.cde_dict["max_value"])
        return ",".join(vals)

    def _get_allowed_values(self):
        pvg_code = self.cde_dict["pv_group"]
        if pvg_code:
            for pvg in self.data["pvgs"]:
                if pvg_code == pvg["code"]:
                    display_values = []
                    for pv in pvg["values"]:
                        display_value = pv["value"]
                        # stored_value = pv["code"]
                        display_values.append(display_value)
                    return display_values
            return []
        else:
            return []


class DataDefinitionReport(object):

    def __init__(self, data, stream):
        self.data = data
        self.stream = stream
        self.current_line = []
        self.line_num = 1
        self.delimiter = "\t"

    def write_column(self, value):
        self.current_line.append(value)

    def new_line(self):
        print("writing line: %s" % self.current_line)
        # encoded = map(lambda s : s.decode('utf-8'), self.current_line)
        line = self.delimiter.join(self.current_line)
        line = line + "\n"
        self.stream.write(line)
        self.current_line = []
        self.line_num += 1

    def write_values(self, *values):
        for value in values:
            self.write_column(value)

        self.new_line()

    def write_header(self):
        self.write_values("FIELDNUM", "FORM", "SECTION", "CDE",
                          "DATATYPE", "REQUIRED", "ALLOWED VALUES", "VALIDATION")

    def _get_cdes_from_section(self, section_dict):
        cdes = []
        cde_codes = map(strip, section_dict["elements"])
        for cde_code in cde_codes:
            cde_dict = self._get_cde_dict(cde_code)
            cde = CDEWrapper(self.data, cde_dict)
            cdes.append(cde)
        return cdes

    def _get_cde_dict(self, cde_code):
        for cde_dict in self.data["cdes"]:
            if cde_dict["code"] == cde_code:
                return cde_dict

    def _get_demographic_fields(self):
        fields = []
        fields.append(DemographicField(
            DemographicForm.SECTION_REGISTRY, "Centre", required=True))
        # fields.append(DemographicField(DemographicForm.SECTION_REGISTRY, "Clinician"))
        fields.append(DemographicField(
            DemographicForm.SECTION_PATIENT_DETAILS, "Family name", required=True))
        fields.append(DemographicField(
            DemographicForm.SECTION_PATIENT_DETAILS, "Given names", required=True))
        fields.append(DemographicField(
            DemographicForm.SECTION_PATIENT_DETAILS, "Maiden name"))
        fields.append(DemographicField(
            DemographicForm.SECTION_PATIENT_DETAILS, "Hospital/Clinic ID"))
        fields.append(DemographicField(
            DemographicForm.SECTION_PATIENT_DETAILS, "Date of birth", "DATE", required=True))
        fields.append(DemographicField(
            DemographicForm.SECTION_PATIENT_DETAILS, "Country of birth", "RANGE", COUNTRIES))
        fields.append(DemographicField(
            DemographicForm.SECTION_PATIENT_DETAILS, "Ethnic Origin", "RANGE", ETHNICITIES))
        fields.append(DemographicField(
            DemographicForm.SECTION_PATIENT_DETAILS, "Sex", "RANGE", SEXES, required=True))
        fields.append(DemographicField(
            DemographicForm.SECTION_PATIENT_DETAILS, "Home Phone"))
        fields.append(DemographicField(
            DemographicForm.SECTION_PATIENT_DETAILS, "Mobile Phone"))
        fields.append(DemographicField(
            DemographicForm.SECTION_PATIENT_DETAILS, "Work Phone"))
        fields.append(DemographicField(
            DemographicForm.SECTION_PATIENT_DETAILS, "Email"))
        fields.append(
            DemographicField(
                DemographicForm.SECTION_PATIENT_DETAILS,
                "Living status",
                "RANGE",
                LIVING_STATUSES,
                required=True))
        fields.append(DemographicField(
            DemographicForm.HOME_ADDRESS, "Address"))
        fields.append(DemographicField(
            DemographicForm.HOME_ADDRESS, "Suburb/Town"))
        fields.append(DemographicField(
            DemographicForm.HOME_ADDRESS, "State", "RANGE", AUS_STATES))
        fields.append(DemographicField(
            DemographicForm.HOME_ADDRESS, "Postcode"))
        fields.append(DemographicField(
            DemographicForm.HOME_ADDRESS, "Country", "RANGE", COUNTRIES))

        return fields

    def _get_consent_fields(self):
        fields = []

        def mk_consent(sec, field, required=False):
            fields.append(DemographicField(sec, field, "RANGE", BOOLEAN, required=required))

        mk_consent("FH Registry Consent", "Adult Consent")
        mk_consent("FH Registry Consent", "Child Consent")
        mk_consent("FH Optional Consents", "Clinical Trials")
        mk_consent("FH Optional Consents", "Information")
        mk_consent("FH Registry Subset", "FCHL")
        mk_consent("FH Registry Subset", "Hyper-Lp(a)")
        return fields

    def __iter__(self):
        col = 1

        # first column is the oroginal patient ID in their system
        yield "1", "NA", "NA", "YOURPATIENTID", "NA", "True", "", ""
        col += 1

        for demographic_field in self._get_demographic_fields():
            yield str(col), "DEMOGRAPHICS", demographic_field.section, demographic_field.name, demographic_field.datatype, demographic_field.required, demographic_field.members, demographic_field.validation
            col += 1

        for field in self._get_consent_fields():
            yield str(col), "CONSENTS", field.section, field.name, field.datatype, field.required, field.members, field.validation
            col += 1

        for form_dict in self.data["forms"]:
            if form_dict["name"] == "FollowUp":
                continue
            for section_dict in form_dict["sections"]:
                if not section_dict["allow_multiple"]:
                    cdes = self._get_cdes_from_section(section_dict)
                    for cde in cdes:
                        yield str(col), form_dict["name"], section_dict["display_name"], cde.name, cde.datatype, cde.required, cde.members, cde.validation

                        col += 1


yaml_file = sys.argv[1]
output_file = sys.argv[2]


with open(yaml_file) as yf:
    data = yaml.load(yf)

f = codecs.open(output_file, mode="w", encoding="utf-8")
ddr = DataDefinitionReport(data, f)
ddr.write_header()
for items in ddr:
    ddr.write_values(*items)
