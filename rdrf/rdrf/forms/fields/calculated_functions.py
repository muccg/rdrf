# flake8: noqa
# Ignore pep8 linting for a while - the code matching the JS calculated field it will make it easier to find the difference.
# This decision was taken in August 2019 - by 2020 the code should have been in prod for some time - you can then fix all pep8
# WARNING: you CANNOT change the name of the CDE function so you must ignore the linting for them as they must have uppercase
# to match the calculated cde codes.

from rest_framework.exceptions import ParseError
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import math
import logging
logger = logging.getLogger(__name__)

# This module (file) contains the calulated fields functions.
# What are calculated field:
# CDE can be read-only field that are automatically calculated. We call them calculated fields. Their values are set by
# the functions
# These field are created and set by us, RDRF developer as we are the maintainer of these CDE calculation.
# The RDRF designer can still edit these field in the administration but can not change the calculations.
# They must not change the CDE code.

# The input text are always set by the front end to empty string when they are not filled.
# However when these calculated functions are called by command line, the input which are not filled are not set because
# get_form_value do not return them.


def fill_missing_input(context, input_func_name):
    mod = __import__('rdrf.forms.fields.calculated_functions', fromlist=['object'])
    func = getattr(mod, input_func_name)
    for cde_code in func():
        if cde_code not in context.keys():
            context[cde_code] = ""
    return context


####################### BEGIN OF CDEfhDutchLipidClinicNetwork ###################################

def bad(value):
    return (value is None) or (math.isnan(value))


def calculate_age(dob, assessmentDate):
    age = assessmentDate.year - dob.year
    m = assessmentDate.month - dob.month
    if m < 0 or (m == 0 and assessmentDate.day < dob.day):
        age = age - 1
    return age


def getLDL(context):
    untreated = context["CDE00013"]
    adjusted = context["LDLCholesterolAdjTreatment"]
    try:
        L = float(untreated)
        if math.isnan(L):
            raise Exception(f"untreated not filled out")
        return L
    except:
        try:
            # try adjusted value
            L = float(adjusted)
            if not math.isnan(L):
                return L
            else:
                return None
        except:
            return None


def getScore(context, patient):
    assessmentDate = context["DateOfAssessment"]

    isAdult = calculate_age(patient["date_of_birth"], validate_date(assessmentDate)) >= 18
    index = context["CDEIndexOrRelative"] == "fh_is_index"
    relative = context["CDEIndexOrRelative"] == "fh_is_relative"

    YES = "fh2_y"

    # family history
    FAM_HIST_PREM_CVD_FIRST_DEGREE_RELATIVE = context["CDE00004"]
    FAM_HIST_HYPERCHOL_FIRST_DEGREE_RELATIVE = context["CDE00003"]
    FAM_HIST_CHILD_HYPERCOL = context["FHFamilyHistoryChild"]
    YES_CHILD = "y_childunder18"
    FAM_HIST_TENDON_FIRST_DEGREE_RELATIVE = context["FHFamHistTendonXanthoma"]
    FAM_HIST_ARCUS_CORNEALIS_FIRST_DEGREE_RELATIVE = context["FHFamHistArcusCornealis"]

    # clinical history
    PERS_HIST_COR_HEART = context["CDE00011"]
    HAS_COR_HEART_DISEASE = "fhpremcvd_yes_corheartdisease"
    PERS_HIST_CVD = context["FHPersHistCerebralVD"]

    # physical examination
    TENDON_XANTHOMA = context["CDE00001"]
    ARCUS_CORNEALIS = context["CDE00002"]

    def familyHistoryScore():
        score = 0

        if ((FAM_HIST_PREM_CVD_FIRST_DEGREE_RELATIVE == YES) or (FAM_HIST_HYPERCHOL_FIRST_DEGREE_RELATIVE == YES)):
            score += 1

        if (((FAM_HIST_TENDON_FIRST_DEGREE_RELATIVE == YES) or (
                FAM_HIST_ARCUS_CORNEALIS_FIRST_DEGREE_RELATIVE == YES)) or (FAM_HIST_CHILD_HYPERCOL == YES_CHILD)):
            score += 2

        if score > 2:
            score = 2

        return score

    def clinicalHistoryScore():
        score = 0

        if (PERS_HIST_COR_HEART == HAS_COR_HEART_DISEASE):
            score += 2

        if (PERS_HIST_CVD == YES):
            score += 1

        if score > 2:
            score = 2

        return score

    def physicalExaminationScore():
        score = 0

        if (TENDON_XANTHOMA == "y"):
            score += 6

        if (ARCUS_CORNEALIS == "y"):
            score += 4

        if score > 6:
            score = 6

        return score

    def investigationScore():
        L = getLDL(context)

        if bad(L):
            raise Exception(f"Please fill in LDL values")
        else:
            score = 0

            if (4.0 <= L) and (L < 5.0):
                score += 1

            # NB the sheet uses <= 6.4 but technically we could have L = 6.45 say
            # whicn using the sheet would give undefined ...
            # add 3 to score if 5.0 <= L <= 6.4
            if (5.0 <= L) and (L < 6.5):
                score += 3

            # add 5 to score if 6.5 <= L <= 8.4
            if (6.5 <= L) and (L < 8.5):
                score += 5

            # add 8 to score if L >= 8.5
            if L >= 8.5:
                score += 8

            return score

    if index:
        if isAdult:

            try:
                score = familyHistoryScore() + clinicalHistoryScore() + physicalExaminationScore() + investigationScore()
                return score
            except:
                return ""
        else:
            # child  - score not used ( only categorisation )
            return ""

    else:
        if relative:
            # relative  - score not used ( only categorisation )
            return ""


def CDEfhDutchLipidClinicNetwork(patient, context):

    context = fill_missing_input(context, 'CDEfhDutchLipidClinicNetwork_inputs')

    if context["DateOfAssessment"] is None or context["DateOfAssessment"] == "":
        return ""
    score = getScore(context, patient)

    if score is None:
        return ""

    return str(score)


def CDEfhDutchLipidClinicNetwork_inputs():
    return ["DateOfAssessment", "CDEIndexOrRelative", "CDE00004", "CDE00003", "FHFamilyHistoryChild", "FHFamHistTendonXanthoma",
            "FHFamHistArcusCornealis", "CDE00011", "FHPersHistCerebralVD", "CDE00001", "CDE00002", "CDE00013", "LDLCholesterolAdjTreatment"]

################ END OF CDEfhDutchLipidClinicNetwork ################################


################ BEGINNING OF CD00024 ################################

def getFloat(x):
    if x is not None:
        y = float(x)
        if not math.isnan(y):
            return y
    return None


def getFilledOutScore(x, y):
    xval = getFloat(x)
    if xval is not None:
        return xval
    return getFloat(y)


def CDE00024_getLDL(context):
    untreated = context["CDE00013"]
    adjusted = context["LDLCholesterolAdjTreatment"]
    return getFilledOutScore(untreated, adjusted)


def catchild(context):
    # for index patients
    L = CDE00024_getLDL(context)
    if bad(L):
        return ""

    def anyrel(context):
        return (context["CDE00003"] == "fh2_y") or (context["CDE00004"] == "fh2_y") or (
            context["FHFamHistTendonXanthoma"] == "fh2_y") or (context["FHFamHistArcusCornealis"] == "fh2_y")

    # Definite if DNA Analysis is Yes
    # other wise
    if L > 5.0:
        return "Highly Probable"

    if L >= 4.0 and anyrel(context):
        return "Probable"

    if L >= 4.0:
        return "Possible"

    return "Unlikely"


def catadult(score):
    # for index patients
    if bad(score):
        return ""

    if score == "":
        return ""

    if score < 3:
        return "Unlikely"

    if (3 <= score) and (score < 6):
        return "Possible"

    if (6 <= score) and (score <= 8):
        return "Probable"

    return "Definite"


def catrelative(sex, age, lipid_score):
    if bad(lipid_score):
        return ""

    table = None
    BIG = 99999999999999.00
    MALE_TABLE = [
        # AGE        Unlikely     Uncertain       Likely
        [[0, 14], [[-1, 3.099], [3.1, 3.499], [3.5, BIG]]],
        [[15, 24], [[-1, 2.999], [3.0, 3.499], [3.5, BIG]]],
        [[25, 34], [[-1, 3.799], [3.8, 4.599], [4.6, BIG]]],
        [[35, 44], [[-1, 3.999], [4.0, 4.799], [4.8, BIG]]],
        [[45, 54], [[-1, 4.399], [4.4, 5.299], [5.3, BIG]]],
        [[55, 999], [[-1, 4.299], [4.3, 5.299], [5.3, BIG]]]]

    FEMALE_TABLE = [
        # AGE         Unlikely    Uncertain       Likely
        [[0, 14], [[-1, 3.399], [3.4, 3.799], [3.8, BIG]]],
        [[15, 24], [[-1, 3.299], [3.3, 3.899], [3.9, BIG]]],
        [[25, 34], [[-1, 3.599], [3.6, 4.299], [4.3, BIG]]],
        [[35, 44], [[-1, 3.699], [3.7, 4.399], [4.4, BIG]]],
        [[45, 54], [[-1, 3.999], [4.0, 4.899], [4.9, BIG]]],
        [[55, 999], [[-1, 4.399], [4.4, 5.299], [5.3, BIG]]]]

    def inRange(value, a, b):
        return (value >= a) and (value <= b)

    def lookupCat(cat_age, cat_score, cat_table):
        cats = ["Unlikely", "Uncertain", "Likely"]
        for i in range(0, len(cat_table)):
            row = cat_table[i]
            ageInterval = row[0]
            ageMin = ageInterval[0]
            ageMax = ageInterval[1]
            if (inRange(cat_age, ageMin, ageMax)):
                catRanges = row[1]
                for j in range(0, 3):
                    ranges = catRanges[j]
                    rangeMin = ranges[0]
                    rangeMax = ranges[1]

                    if (inRange(cat_score, rangeMin, rangeMax)):
                        category = cats[j]
                        return category
        return ""

    if sex == '1':
        table = MALE_TABLE

    if sex == '2':
        table = FEMALE_TABLE

    if table is None:
        return ""

    return lookupCat(age, lipid_score, table)


def categorise(context, patient):
    dutch_lipid_network_score = None if context["CDEfhDutchLipidClinicNetwork"] == "" else validate_float(
        context["CDEfhDutchLipidClinicNetwork"])
    assessmentDate = validate_date(context["DateOfAssessment"])
    isAdult = calculate_age(patient["date_of_birth"], assessmentDate) >= 18.0
    index = context["CDEIndexOrRelative"] == "fh_is_index"
    relative = context["CDEIndexOrRelative"] == "fh_is_relative"

    if (index):
        if (isAdult):
            return catadult(dutch_lipid_network_score)
        return catchild(context)

    if (relative):
        age = calculate_age(patient["date_of_birth"], assessmentDate)
        L = CDE00024_getLDL(context)
        sex = patient["sex"]
        cr = catrelative(sex, age, L)
        return cr


def CDE00024(patient, context):

    context = fill_missing_input(context, 'CDE00024_inputs')

    if context["DateOfAssessment"] is None or context["DateOfAssessment"] == "":
        return ""

    category = categorise(context, patient)

    if category is None:
        return ""

    return str(category)


def CDE00024_inputs():
    return ["CDEIndexOrRelative", "DateOfAssessment", "CDEfhDutchLipidClinicNetwork", "FHFamHistTendonXanthoma", "FHFamHistArcusCornealis",
            "CDE00003", "CDE00004", "LDLCholesterolAdjTreatment", "CDE00013"]


################ END OF CD00024 ################################

################ BEGINNING OF LDLCholesterolAdjTreatment ################################

# helper functions
def correction_factor(dose):
    # Correction values for each PV:
    table = {
        "FAAtorvastatin10": 1.618123,
        "FAAtorvastatin20": 1.763668,
        "FAAtorvastatin40": 1.937984,
        "FAAtorvastatin80": 2.150538,
        "FARosuvastatin5": 1.709402,
        "FARosuvastatin10": 1.872659,
        "FARosuvastatin20": 2.070393,
        "FARosuvastatin40": 2.314815,
        "FARosuvastatin80": 2.624672,
        "FASimvastatin10": 1.37741,
        "FASimvastatin20": 1.492537,
        "FASimvastatin40": 1.636661,
        "FASimvastatin80": 1.818182,
        "FAEzetimibe10": 1.236094,
        "FAEzetimibe/simvastatin10": 1.855288,
        "FAEzetimibe/simvastatin20": 2.008032,
        "FAEzetimibe/simvastatin40": 2.252252,
        "FAEzetimibe/simvastatin80": 2.463054,
        "FAEzetimibe/atorvastatin10": 2,
        "FAEzetimibe/atorvastatin20": 2.173913,
        "FAEzetimibe/atorvastatin40": 2.173913,
        "FAEzetimibe/atorvastatin80": 2.5,
        "FAEzetimibe/rosuvastatin10": 2.48139,
        "FAEzetimibe/rosuvastatin20": 2.739726,
        "FAEzetimibe/rosuvastatin40": 3.333333,
        "FAPravastatin10": 1.251564,
        "FAPravastatin20": 1.322751,
        "FAPravastatin40": 1.422475,
        "FAOther": 1.43,
    }

    try:
        return table[dose]
    except:
        return 0.0


def roundToTwo(num):
    # rounding function: 1.0049 => 1.00, 1.0050 => 1.01, 1.0060 => 1.01
    return Decimal(num).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)


def LDLCholesterolAdjTreatment(patient, context):

    context = fill_missing_input(context, 'LDLCholesterolAdjTreatment_inputs')

    # if empty CDE000019 return a NaN error
    if context["CDE00019"] is None or context["CDE00019"] == "":
        return "NaN"

    # if empty PlasmaLipidTreatment return a NaN error
    if context["PlasmaLipidTreatment"] is None or context["PlasmaLipidTreatment"] == "":
        return "NaN"

    ldl_chol = context["CDE00019"]
    # Dosage
    dose = context["PlasmaLipidTreatment"]

    try:
        LDLCholesterolAdjTreatment = str(roundToTwo(Decimal(str(ldl_chol * correction_factor(dose)))))
        # remove trailing 0: 14.23 => 14.23, 14.20 => 14.2, 14.00 => 14
        trimmed_LDLCholesterolAdjTreatment = LDLCholesterolAdjTreatment.rstrip('0').rstrip(
            '.') if '.' in LDLCholesterolAdjTreatment else LDLCholesterolAdjTreatment
        return trimmed_LDLCholesterolAdjTreatment

    except:
        return ""


def LDLCholesterolAdjTreatment_inputs():
    return ["PlasmaLipidTreatment", "CDE00019"]


################ END OF LDLCholesterolAdjTreatment ################################

################ BEGINNING OF CDEBMI ################################

def CDEBMI(patient, context):

    context = fill_missing_input(context, 'CDEBMI_inputs')

    height = context["CDEHeight"]
    weight = context["CDEWeight"]

    # Simulating weird behaviour to match the current JS calculation results
    # Hopefull we decide later to remove this behaviour but in a first stage in converting the JS calculation in python
    # we try to match the exact result of the JS calculation (even thought they may be wrong like this problem with "" / NUMBER => 0)
    if not weight and height:
        return "0"

    if not height or not weight:
        return "NaN"

    bmi = weight / (height * height)

    CDEBMI = str(roundToTwo(bmi))
    # remove trailing 0: 14.23 => 14.23, 14.20 => 14.2, 14.00 => 14
    trimmed_CDEBMI = CDEBMI.rstrip('0').rstrip('.') if '.' in CDEBMI else CDEBMI
    return trimmed_CDEBMI


def CDEBMI_inputs():
    return ["CDEHeight", "CDEWeight"]


################ END OF CDEBMI ################################

################ BEGINNING OF FHDeathAge ################################
epoch = datetime.utcfromtimestamp(0)


def unix_time_millis(dt):
    return (dt - epoch).total_seconds() * 1000.0


def FHDeathAge(patient, context):

    context = fill_missing_input(context, 'FHDeathAge_inputs')

    if not context["FHDeathDate"]:
        return "NaN"

    deathDate = validate_date(context["FHDeathDate"])
    birthDate = patient["date_of_birth"]
    deathAge = calculate_age(birthDate, deathDate)

    if deathAge is None or deathAge == "":
        return None

    return str(deathAge)


def FHDeathAge_inputs():
    return ["FHDeathDate"]

################ END OF FHDeathAge ################################

################ BEGINNING OF fhAgeAtConsent ################################


def fhAgeAtConsent(patient, context):

    context = fill_missing_input(context, 'fhAgeAtConsent_inputs')

    if not context["FHconsentDate"]:
        return "NaN"

    consentDate = validate_date(context["FHconsentDate"])
    birthDate = patient["date_of_birth"]
    consentAge = calculate_age(birthDate, consentDate)

    if consentAge is None or consentAge == "":
        return None

    return str(consentAge)


def fhAgeAtConsent_inputs():
    return ["FHconsentDate"]

################ END OF fhAgeAtConsent ################################

################ BEGINNING OF fhAgeAtAssessment ################################


def fhAgeAtAssessment(patient, context):

    context = fill_missing_input(context, 'fhAgeAtAssessment_inputs')

    if not context["DateOfAssessment"]:
        return "NaN"

    assessmentDate = validate_date(context["DateOfAssessment"])
    birthDate = patient["date_of_birth"]
    assessmentAge = calculate_age(birthDate, assessmentDate)

    if assessmentAge is None or assessmentAge == "":
        return None

    return str(assessmentAge)


def fhAgeAtAssessment_inputs():
    return ["DateOfAssessment"]

################ END OF fhAgeAtAssessment ################################


################ BEGINNING OF DDAgeAtDiagnosis ################################

def DDAgeAtDiagnosis(patient, context):

    context = fill_missing_input(context, 'DDAgeAtDiagnosis_inputs')

    if not context["DateOfDiagnosis"]:
        return "NaN"

    diagnosisDate = validate_date(context["DateOfDiagnosis"])
    birthDate = patient["date_of_birth"]
    deathAge = calculate_age(birthDate, diagnosisDate)

    if deathAge is None or deathAge == "":
        return None

    return str(deathAge)


def DDAgeAtDiagnosis_inputs():
    return ["DateOfDiagnosis"]

################ END OF DDAgeAtDiagnosis ################################


################ BEGINNING OF poemScore ################################

DAYS0 = "NoDays"
DAYS1TO2 = "1to2Days"
DAYS3TO4 = "3to4Days"
DAYS5TO6 = "5to6Days"
EVERYDAY = "EveryDay"


def convert(val):
    if val == DAYS0:
        return 0
    if val == DAYS1TO2:
        return 1
    if val == DAYS3TO4:
        return 2
    if val == DAYS5TO6:
        return 3
    if val == EVERYDAY:
        return 4
    return -1


def getQ(cde):
    try:
        return convert(cde)
    except:
        return 0


def getCategory(score):
    if score <= 2:
        return "Clear or almost clear"
    if score <= 7:
        return "Mild eczema"
    if score <= 16:
        return "Moderate eczema"
    if score <= 24:
        return "Severe eczema"
    if score <= 28:
        return "Very severe eczema"
    return ""


def poemScore(patient, context):

    context = fill_missing_input(context, 'poemScore_inputs')

    q1 = context["poemQ1"]
    q2 = context["poemQ2"]
    q3 = context["poemQ3"]
    q4 = context["poemQ4"]
    q5 = context["poemQ5"]
    q6 = context["poemQ6"]
    q7 = context["poemQ7"]

    answers = [getQ(q1), getQ(q2), getQ(q3), getQ(q4), getQ(q5), getQ(q6), getQ(q7)]
    counts = {}

    for i in range(0, len(answers)):
        answer = str(answers[i])
        if answer in counts.keys():
            counts[answer] = counts[answer] + 1
        else:
            counts[answer] = 1

    if "-1" in counts.keys() and counts["-1"] >= 2:
        result = "UNSCORED"
    else:
        # Change answers -1 into 0.
        # We previously set unanswered questions to -1 to differentiate then from 0days (as 0days equals 0)
        # but now that we are going to calculate the total score, so we want the unanswered questions
        # to not affect the final score and so to be set to 0.
        fixed_answers = [answer if answer != -1 else 0 for answer in answers]
        s = sum(fixed_answers)
        cat = getCategory(s)
        result = s.__str__() + " ( " + cat + " )"

    return result


def poemScore_inputs():
    return ["poemQ1", "poemQ2", "poemQ3", "poemQ4", "poemQ5", "poemQ6", "poemQ7", ]

################ END OF poemScore ################################

################ BEGINNING OF ANGCurrentPatientAge ################################

def ANGCurrentPatientAge(patient, context):

    if not patient["date_of_birth"]:
        return "NaN"

    todayDate = datetime.now()
    birthDate = patient["date_of_birth"]
    currentPatientAge = calculate_age(birthDate, todayDate)

    if currentPatientAge is None or currentPatientAge == "":
        return None

    return str(currentPatientAge)

def ANGCurrentPatientAge_inputs():
    return []

################ END OF ANGCurrentPatientAge ################################

################ BEGINNING OF ANGBMImetric ################################

def ANGBMImetric(patient, context):

    context = fill_missing_input(context, 'ANGBMImetric_inputs')

    height = context["ANGObesityHeight"]
    weight = context["ANGObesityWeight"]

    # Simulating weird behaviour to match the current JS calculation results
    # Hopefull we decide later to remove this behaviour but in a first stage in converting the JS calculation in python
    # we try to match the exact result of the JS calculation (even thought they may be wrong like this problem with "" / NUMBER => 0)
    if not weight and height:
        return "0"

    if not height or not weight:
        return "NaN"

    bmi = weight / (height * height)

    ANGObesityBMI = str(roundToTwo(bmi))
    # remove trailing 0: 14.23 => 14.23, 14.20 => 14.2, 14.00 => 14
    trimmed_ANGObesityBMI = ANGObesityBMI.rstrip('0').rstrip('.') if '.' in ANGObesityBMI else ANGObesityBMI
    return trimmed_ANGObesityBMI


def ANGBMImetric_inputs():
    return ["ANGObesityHeight", "ANGObesityWeight"]


################ END OF ANGBMImetric ################################

################ BEGINNING OF ANGBMIimperial ################################

def ANGBMIimperial(patient, context):

    context = fill_missing_input(context, 'ANGBMIimperial_inputs')

    feet = context["ANGObesityHeightft"]
    inches = context["ANGHeightIn"]
    weight = context["ANGObesityWeightlb"]

    # Simulating weird behaviour to match the current JS calculation results
    # Hopefull we decide later to remove this behaviour but in a first stage in converting the JS calculation in python
    # we try to match the exact result of the JS calculation (even thought they may be wrong like this problem with "" / NUMBER => 0)
    if not weight and (feet or inches):
        return "0"

    if not feet or not inches or not weight:
        return "NaN"

    height = feet * 12 + inches

    bmi = (weight * 703) / (height * height)

    ANGimperialBMI = str(roundToTwo(bmi))
    # remove trailing 0: 14.23 => 14.23, 14.20 => 14.2, 14.00 => 14
    trimmed_ANGimperialBMI = ANGimperialBMI.rstrip('0').rstrip('.') if '.' in ANGimperialBMI else ANGimperialBMI
    return trimmed_ANGimperialBMI

def ANGBMIimperial_inputs():
    return ["ANGObesityHeightft", "ANGHeightIn", "ANGObesityWeightlb"]

################ END OF ANGBMIimperial ################################

def validate_date(date):
    try:
        return datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        raise ParseError(detail="Bad date format")

def validate_float(tocast):
    try:
        return float(tocast)
    except ValueError:
        raise ParseError(detail="Not a float")