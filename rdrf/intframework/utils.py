# flake8: noqa
import hl7
import logging
from datetime import datetime
from typing import Optional, Tuple
import re

logger = logging.getLogger(__name__)

field_pattern = re.compile("^(.*\.F\d+).*$")


def get_segment_field(path):
    # from PID.F13.R1.C3  we want
    # PID.F13 returned as a pair : "PID", "F13"
    m = field_pattern.search(path)
    if m:
        field_path = m.group(1)
        segment, field = field_path.split(".")
        return segment, field
    return None


def field_empty(message: hl7.Message, path: str) -> bool:
    # path is something like PID.F13
    segment, field_expr = get_segment_field(path)
    field_num = int(field_expr.replace("F", ""))
    hl7_field = message[segment][0][field_num]  # this is an object
    field_value = f"{hl7_field}"
    if not field_value:
        return True
    else:
        return False


def get_umrn(message: hl7.Message) -> str:
    try:
        umrn = message["PID.F3"]
        return umrn
    except Exception as ex:
        logger.error(ex)
        return ""


def get_event_code(message: hl7.Message) -> str:
    logger.info("get event code ")
    try:
        ec = message["MSH.F9.R1.C3"]  # ADR_A19  message structure
        if not len(ec):
            raise Exception
        logger.info("event code = %s" % ec)
        return ec
    except Exception as ex:
        logger.error(ex)
        try:
            ec = f'{message["MSH.F9.R1.C1"]}_{message["MSH.F9.R1.C2"]}'  # message code and trigger event
            logger.info("event code = %s" % ec)
            return ec
        except Exception as ex:
            logger.error(ex)
            return "error"


def patient_found(message: hl7.Message) -> bool:
    """
    patient found == message contains PID segment
    """
    try:
        message["PID"]
        return True
    except Exception:
        pass
    return False


def patient_subscribed(message: hl7.Message) -> bool:
    """
    Look for AA status code of MSA Accept Acknowledgement Code
    """
    try:
        return message["MSA.1"] == "AA"
    except Exception:
        pass
    return False


class TransformFunctionError(Exception):
    pass


class FieldSource:
    LOCAL = "local"
    EXTERNAL = "external"


def get_field_source(cde_code):
    from intframework.models import HL7Mapping

    key = f"/{cde_code}"
    for hl7_mapping in HL7Mapping.objects.all():
        mapping_dict = hl7_mapping.load()
        for field_moniker in mapping_dict:
            if field_moniker.endswith(key):
                return FieldSource.EXTERNAL
    return FieldSource.LOCAL


def transform(func):
    """
    Decorator to mark a function as a transform
    """
    func.hl7_transform_func = True
    return func


@transform
def identity(hl7_value):
    return hl7_value


@transform
def date(hl7_value):
    if hl7_value == '""':
        return None
    if hl7_value == "":
        return None
    return datetime.strptime(hl7_value[:8], "%Y%m%d")


@transform
def rdrf_date(hl7_value):
    date_object = date(hl7_value).date()
    s = "%s-%s-%s" % (date_object.year,
                      date_object.month,
                      date_object.day)
    return s


"""
HL7 values
Value	Description
F	    Female
M	    Male
O	    Other
U	    Unknown
A	    Ambiguous
N	    Not applicable
"""
SEX_MAP = {"M": 1, "F": 2, "U": 3, "O": 3, "A": 3, "N": 3}


CODE_TABLES = {"place_of_birth":
               {'0901': 'New South Wales',
                '0902': 'Victoria',
                '0903': 'Queensland',
                '0904': 'South Australia',
                '0905': 'Western Australia',
                '0906': 'Tasmania',
                '0907': 'Northern Territory',
                '0908': 'Aust Cap Territory',
                '0909': 'Christmas Cocos Island',
                '1101': 'Australia',
                '1102': 'Norfolk Island',
                '1199': 'Australian External Territories, nec',
                '1201': 'New Zealand', '1301': 'New Caledonia',
                '1302': 'Papua New Guinea',
                '1303': 'Solomon Islands',
                '1304': 'Vanuatu',
                '1401': 'Guam',
                '1402': 'Kiribati',
                '1403': 'Marshall Islands',
                '1404': 'Micronesia, Federated States of',
                '1405': 'Nauru',
                '1406': 'Northern Mariana Islands',
                '1407': 'Palau',
                '1501': 'Cook Islands',
                '1502': 'Fiji',
                '1503': 'French Polynesia',
                '1504': 'Niue',
                '1505': 'Samoa',
                '1506': 'Samoa, American',
                "1507":  "Tokelau",
                "1508":  "Tonga",
                "1511":  "Tuvalu",
                "1512":  "Wallis and Futuna",
                "1513":  "Pitcairn Islands",
                "1599":  "Polynesia (excludes Hawaii), nec",
                "1601":  "Adelie Land (France)",
                "1602":  "Argentinian Antarctic Territory",
                "1603":  "Australian Antarctic Territory",
                "1604":  "British Antarctic Territory",
                "1605":  "Chilean Antarctic Territory",
                "1606":  "Queen Maud Land (Norway)",
                "1607":  "Ross Dependency (New Zealand)",
                "2102":  "England",
                "2103":  "Isle of Man",
                "2104":  "Northern Ireland",
                "2105":  "Scotland",
                "2106":  "Wales",
                "2107":  "Guernsey",
                "2108":  "Jersey",
                "2201":  "Ireland",
                "2301":  "Austria",
                "2302":  "Belgium",
                "2303":  "France",
                "2304":  "Germany",
                "2305":  "Liechtenstein",
                "2306":  "Luxembourg",
                "2307":  "Monaco",
                "2308":  "Netherlands",
                "2311":  "Switzerland",
                "2401":  "Denmark",
                "2402":  "Faroe Islands",
                "2403":  "Finland",
                "2404":  "Greenland",
                "2405":  "Iceland",
                "2406":  "Norway",
                "2407":  "Sweden",
                "2408":  "Aland Islands",
                "3101":  "Andorra",
                "3102":  "Gibraltar",
                "3103":  "Holy See",
                "3104":  "Italy",
                "3105":  "Malta",
                "3106":  "Portugal",
                "3107":  "San Marino",
                "3108":  "Spain",
                "3201":  "Albania",
                "3202":  "Bosnia and Herzegovina",
                "3203":  "Bulgaria",
                "3204":  "Croatia",
                "3205":  "Cyprus",
                "3206":  "Former Yugoslav Republic of Macedonia (FYROM)",
                "3207":  "Greece",
                "3208":  "Moldova",
                "3211":  "Romania",
                "3212":  "Slovenia",
                "3214":  "Montenegro",
                "3215":  "Serbia",
                "3216":  "Kosovo",
                "3301":  "Belarus",
                "3302":  "Czech Republic",
                "3303":  "Estonia",
                "3304":  "Hungary",
                "3305":  "Latvia",
                "3306":  "Lithuania",
                "3307":  "Poland",
                "3308":  "Russian Federation",
                "3311":  "Slovakia",
                "3312":  "Ukraine",
                "4101":  "Algeria",
                "4102":  "Egypt",
                "4103":  "Libya",
                "4104":  "Morocco",
                "4105":  "Sudan",
                "4106":  "Tunisia",
                "4107":  "Western Sahara",
                "4108":  "Spanish North Africa",
                "4111":  "South Sudan",
                "4201":  "Bahrain",
                "4202":  "Gaza Strip and West Bank",
                "4203":  "Iran",
                "4204":  "Iraq",
                "4205":  "Israel",
                "4206":  "Jordan",
                "4207":  "Kuwait",
                "4208":  "Lebanon",
                "4211":  "Oman",
                "4212":  "Qatar",
                "4213":  "Saudi Arabia",
                "4214":  "Syria",
                "4215":  "Turkey",
                "4216":  "United Arab Emirates",
                "4217":  "Yemen",
                "5101":  "Burma (Republic of the Union of Myanmar)",
                "5102":  "Cambodia",
                "5103":  "Laos",
                "5104":  "Thailand",
                "5105":  "Vietnam",
                "5201":  "Brunei Darussalam",
                "5202":  "Indonesia",
                "5203":  "Malaysia",
                "5204":  "Philippines",
                "5205":  "Singapore",
                "5206":  "Timor-Leste",
                "6101":  "China (excludes SARs and Taiwan)",
                "6102":  "Hong Kong (SAR of China)",
                "6103":  "Macau (SAR of China)",
                "6104":  "Mongolia",
                "6105":  "Taiwan",
                "6201":  "Japan",
                "6202":  "Korea, Democratic People's Republic of (North)",
                "6203":  "Korea, Republic of (South)",
                "7101":  "Bangladesh",
                "7102":  "Bhutan",
                "7103":  "India",
                "7104":  "Maldives",
                "7105":  "Nepal",
                "7106":  "Pakistan",
                "7107":  "Sri Lanka",
                "7201":  "Afghanistan",
                "7202":  "Armenia",
                "7203":  "Azerbaijan",
                "7204":  "Georgia",
                "7205":  "Kazakhstan",
                "7206":  "Kyrgyzstan",
                "7207":  "Tajikistan",
                "7208":  "Turkmenistan",
                "7211":  "Uzbekistan",
                "8101":  "Bermuda",
                "8102":  "Canada",
                "8103":  "St Pierre and Miquelon",
                "8104":  "United States of America",
                "8201":  "Argentina",
                "8202":  "Bolivia, Plurinational State of",
                "8203":  "Brazil",
                "8204":  "Chile",
                "8205":  "Colombia",
                "8206":  "Ecuador",
                "8207":  "Falkland Islands",
                "8208":  "French Guiana",
                "8211":  "Guyana",
                "8212":  "Paraguay",
                "8213":  "Peru",
                "8214":  "Suriname",
                "8215":  "Uruguay",
                "8216":  "Venezuela, Bolivarian Republic of",
                "8299":  "South America, nec",
                "8301":  "Belize",
                "8302":  "Costa Rica",
                "8303":  "El Salvador",
                "8304":  "Guatemala",
                "8305":  "Honduras",
                "8306":  "Mexico",
                "8307":  "Nicaragua",
                "8308":  "Panama",
                "8401":  "Anguilla",
                "8402":  "Antigua and Barbuda",
                "8403":  "Aruba",
                "8404":  "Bahamas",
                "8405":  "Barbados",
                "8406":  "Cayman Islands",
                "8407":  "Cuba",
                "8408":  "Dominica",
                "8411":  "Dominican Republic",
                "8412":  "Grenada",
                "8413":  "Guadeloupe",
                "8414":  "Haiti",
                "8415":  "Jamaica",
                "8416":  "Martinique",
                "8417":  "Montserrat",
                "8421":  "Puerto Rico",
                "8422":  "St Kitts and Nevis",
                "8423":  "St Lucia",
                "8424":  "St Vincent and the Grenadines",
                "8425":  "Trinidad and Tobago",
                "8426":  "Turks and Caicos Islands",
                "8427":  "Virgin Islands, British",
                "8428":  "Virgin Islands, United States",
                "8431":  "St Barthelemy",
                "8432":  "St Martin (French part)",
                "8433":  "Bonaire, Sint Eustatius and Saba",
                "8434":  "Curacao",
                "8435":  "Sint Maarten (Dutch part)",
                "9101":  "Benin",
                "9102":  "Burkina Faso",
                "9103":  "Cameroon",
                "9104":  "Cape Verde",
                "9105":  "Central African Republic",
                "9106":  "Chad",
                "9107":  "Congo, Republic of",
                "9108":  "Congo, Democratic Republic of",
                "9111":  "Cote d'Ivoire",
                "9112":  "Equatorial Guinea",
                "9113":  "Gabon",
                "9114":  "Gambia",
                "9115":  "Ghana",
                "9116":  "Guinea",
                "9117":  "Guinea-Bissau",
                "9118":  "Liberia",
                "9121":  "Mali",
                "9122":  "Mauritania",
                "9123":  "Niger",
                "9124":  "Nigeria",
                "9125":  "Sao Tome and Principe",
                "9126":  "Senegal",
                "9127":  "Sierra Leone",
                "9128":  "Togo",
                "9201":  "Angola",
                "9202":  "Botswana",
                "9203":  "Burundi",
                "9204":  "Comoros",
                "9205":  "Djibouti",
                "9206":  "Eritrea",
                "9207":  "Ethiopia",
                "9208":  "Kenya",
                "9211":  "Lesotho",
                "9212":  "Madagascar",
                "9213":  "Malawi",
                "9214":  "Mauritius",
                "9215":  "Mayotte",
                "9216":  "Mozambique",
                "9217":  "Namibia",
                "9218":  "Reunion",
                "9221":  "Rwanda",
                "9222":  "St Helena",
                "9223":  "Seychelles",
                "9224":  "Somalia",
                "9225":  "South Africa",
                "9226":  "Swaziland",
                "9227":  "Tanzania",
                "9228":  "Uganda",
                "9231":  "Zambia",
                "9232":  "Zimbabwe",
                "9299":  "Southern and East Africa, nec",
                "1000":  "Oceania and Antarctica, nfd",
                "1100":  "Australia (includes External Territories, nfd)",
                "1300":  "Melanesia, nfd",
                "1400":  "Micronesia, nfd",
                "1500":  "Polynesia (excludes Hawaii), nfd",
                "1600":  "Antarctica, nfd",
                "2000":  "North-West Europe, nfd",
                "2100":  "United Kingdom, Channels Islands and Isle of Man, nfd",
                "2300":  "Western Europe, nfd",
                "2400":  "Northern Europe, nfd",
                "3000":  "Southern and Eastern Europe, nfd",
                "3100":  "Southern Europe, nfd",
                "3200":  "South Eastern Europe, nfd",
                "3300":  "Eastern Europe, nfd",
                "4000":  "North Africa and the Middle East, nfd",
                "4100":  "North Africa, nfd",
                "4200":  "Middle East, nfd",
                "5000":  "South-East Asia, nfd",
                "5100":  "Mainland South-East Asia, nfd",
                "5200":  "Maritime South-East Asia, nfd",
                "6000":  "North-East Asia, nfd",
                "6100":  "Chinese Asia (includes Mongolia), nfd",
                "6200":  "Japan and the Koreas, nfd",
                "7000":  "Southern and Central Asia, nfd",
                "7100":  "Southern Asia, nfd",
                "7200":  "Central Asia, nfd",
                "8000":  "Americas, nfd",
                "8100":  "Northern America, nfd",
                "8200":  "South America, nfd",
                "8300":  "Central America, nfd",
                "8400":  "Caribbean, nfd",
                "9000":  "Sub-Saharan Africa, nfd",
                "9100":  "Central and West Africa, nfd",
                "9200":  "Southern and East Africa, nfd",
                "0000":  "Inadequately Described",
                "0001":  "At Sea",
                "0003":  "Not Stated",
                "0004":  "Unknown (for use in economic statistics)",
                "0005":  "Unidentified (for use in economic statistics)",
                "0911":  "Europe, nfd",
                "0912":  "Former USSR, nfd",
                "0913":  "Former Yugoslavia, nfd",
                "0914":  "Czechoslovakia, nfd",
                "0915":  "Kurdistan, nfd",
                "0916":  "East Asia, nfd",
                "0917":  "Asia, nfd",
                "0918":  "Africa, nfd",
                "0921":  "Serbia and Montenegro, nfd",
                "0922":  "Channel Islands, nfd",
                "0924":  "Netherlands Antilles, nfd",
                "0611":  "Europe",
                "0612":  "Europe and the former USSR",
                "0613":  "Former USSR",
                "0614":  "Asia",
                "0615":  "East Asia",
                "0616":  "Africa",
                "0701":  "Africa, nec",
                "0702":  "Americas, nec",
                "0703":  "Asia, nec",
                "0704":  "Belgium and Luxembourg",
                "0705":  "Central America and the Caribbean (excludes Mexico)",
                "0706":  "Christmas Island",
                "0707":  "Cocos (Keeling) Islands",
                "0708":  "Country Conf. Alumina",
                "0711":  "Denmark (includes Greenland and Faroe Islands)",
                "0712":  "Eurodollar Market",
                "0713":  "Europe, nec",
                "0714":  "Falkland Islands (includes South Georgia and South Sandwich Islands)",
                "0715":  "France (includes Andorra and Monaco)",
                "0716":  "French Antilles (Guadeloupe and Martinique)",
                "0717":  "French Southern Territories",
                "0718":  "International Capital Markets",
                "0721":  "International Institutions",
                "0722":  "International Waters",
                "0723":  "Italy (includes Holy See and San Marino)",
                "0724":  "Johnston and Sand Islands",
                "0725":  "Midway Islands",
                "0726":  "Morocco (includes places under Spanish sovereignty)",
                "0727":  "No Country Details",
                "0728":  "Oceania, nec",
                "0741":  "Reserve Bank Gold",
                "0742":  "Ships' and Aircraft Stores",
                "0743":  "Switzerland (includes Liechtenstein)",
                "0744":  "United States Miscellaneous Islands",
                "0745":  "Wake Island",
                "0746":  "Australia (includes External Territories)",
                "0747":  "JPDA (Joint Petroleum Development Area)"}}


def get_code_table_value(table_name, code):
    if table_name in CODE_TABLES:
        table = CODE_TABLES[table_name]
        if code in table:
            return CODE_TABLES[table_name][code]
        else:
            logger.error(f"code table error: {table_name} does not contain {code}")
            return ""
    else:
        logger.error(f"{table_name} is not in CODE_TABLES")
        return ""


@ transform
def sex(hl7_value):
    return f"{SEX_MAP[hl7_value]}"


def parse_demographics_moniker(moniker: str) -> Optional[str]:
    field = None
    if "/" in moniker:
        _, field = moniker.split("/")
    return field


def parse_cde_moniker(moniker: str) -> Optional[Tuple[str, str, str]]:
    # get form_name, section_code, cde_code
    parts = moniker.split("/")
    assert len(parts) == 3
    assert parts[0] != "Demographics"
    pass


def load_message(message_file: str):
    # used for interactive testing
    import io
    import hl7
    from hl7.client import read_loose
    try:
        binary_data = open(message_file, "rb").read()
        stream = io.BytesIO(binary_data)
        raw_messages = [raw_message for raw_message in read_loose(stream)]
        decoded_messages = [rm.decode("ascii") for rm in raw_messages]
        messages = [hl7.parse(dm) for dm in decoded_messages]
        num_messages = len(messages)
        if num_messages > 1:
            return messages[1]
        else:
            return messages[0]
    except hl7.ParseException as pex:
        print(pex)
        return None
    except Exception as ex:
        print(ex)
        return None


class SearchExpressionError(Exception):
    pass


class NotFoundError(Exception):
    pass


class FieldEmpty(Exception):
    pass


class MessageSearcher:
    def __init__(self, field_mapping):
        self.field_mapping = field_mapping
        self.prefix = self.field_mapping["path"]
        self.select = self.field_mapping["select"]
        self.where = self.field_mapping["where"]
        self.num_components = self.field_mapping["num_components"]
        self.repeat = 1

    def get_component(self, repeat, component, message):
        full_key = f"{self.prefix}.R{repeat}.{component}"
        return message[full_key]

    def get_value(self, message: hl7.Message):
        if field_empty(message, self.prefix):
            raise FieldEmpty(self.prefix)

        # otherwise we try to extract the component specified
        r = 1
        stopped = False
        while not stopped:
            try:
                where_actual = self.get_where_dict(r, message)
                if where_actual == self.where:
                    value = self.get_component(r, self.select, message)
                    return value
                r += 1
            except IndexError:
                stopped = True

        raise NotFoundError(str(self))

    def get_where_dict(self, repeat, message):
        return {k: self.get_component(repeat, k, message) for k in self.where}

    def __str__(self):
        w = ""
        for k in sorted(self.where):
            w += f" {k}={self.where[k]}"
        return f"SELECT {self.select} WHERE{w}"


def parse_message_file(registry, user, patient, event_code, message_file):
    from intframework.models import HL7Mapping
    from intframework.hub import MockClient
    model = HL7Mapping.objects.all().get(event_code=event_code)
    mock_client = MockClient(registry, user, None, None)
    parsed_message = mock_client._parse_mock_message_file(message_file)
    parse_dict = model.parse(parsed_message, patient, registry.code)
    return parse_dict


def hl7_field(event_code, field_spec, default_value):
    from intframework.models import HL7MessageConfig
    try:
        message_config = HL7MessageConfig.objects.get(event_code=event_code)
        return message_config.config.get(field_spec, default_value)
    except HL7MessageConfig.DoesNotExist:
        return default_value


def parse_message(message_file):
    """
    A helper for interactive debugging
    """
    from rdrf.models.definition.models import Registry
    from registry.groups.models import CustomUser
    from intframework.hub import MockClient
    registry = Registry.objects.get()
    user = CustomUser.objects.get(username="admin")
    mock_client = MockClient(registry, user, None, None)
    return mock_client._parse_mock_message_file(message_file)


def empty_value_for_field(field):
    if "date_" in field:
        return None
    return ""
