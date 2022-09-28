# flake8: noqa
# Ignore pep8 linting for a while - the code matching the JS calculated field it will make it easier to find the difference.
# This decision was taken in August 2019 - by 2020 the code should have been in prod for some time - you can then fix all pep8
# WARNING: you CANNOT change the name of the CDE function so you must ignore the linting for them as they must have uppercase
# to match the calculated cde codes.

from rest_framework.exceptions import ParseError
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from functools import reduce
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


class AcrossFormsError(Exception):
    pass


class AcrossFormsInfo:
    def __init__(self,
                 registry_model,
                 patient_model):
        self.registry_model = registry_model
        self.patient_model = patient_model

    def _get_location(self, cde_code):
        for form_model in self.registry_model.forms:
            for section_model in form_model.section_models:
                for cde_model in section_model.cde_models:
                    if cde_model.code == cde_code:
                        return form_model, section_model
        return None, None

    def _get_main_context(self):
        context_model = self.patient_model.default_context(self.registry_model)
        return context_model

    def get_cde_value(self, cde_code):
        context_model = self._get_main_context()
        form_model, section_model = self._get_location(cde_code)
        if form_model is None or section_model is None:
            raise AcrossFormsError("Cannot locate %s" % cde_code)
        return self.patient_model.get_form_value(self.registry_model.code,
                                                 form_model.name,
                                                 section_model.code,
                                                 cde_code,
                                                 multisection=False,
                                                 context_id=context_model.id)


def fill_missing_input(context, input_func_name, across_forms_info=None):
    logger.debug(f"fill missing input context = {context}")
    mod = __import__('rdrf.forms.fields.calculated_functions', fromlist=['object'])
    func = getattr(mod, input_func_name)
    if across_forms_info is not None:
        logger.debug("fill_missing_input checking across forms info")
        # the input cdes are on another form
        for cde_code in func():
            logger.debug(f"checking for input cde {cde_code}")
            if cde_code not in context.keys():
                logger.debug(f"{cde_code} not in context - trying across forms")
                try:
                    cde_value = across_forms_info.get_cde_value(cde_code)
                    logger.debug(f"found cde {cde_code} across forms value = {cde_value}")
                except KeyError:
                    logger.debug(f"{cde_code} could not be found across forms")
                    cde_value = ""
                context[cde_code] = cde_value
            else:
                logger.debug(f"input {cde_code} is in context ( value is {context[cde_code]}")
    else:
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

crc_cancer_stage_spec = """Stage Unknown
TNMPTCRC = pTX TNMPNCRC = pNX TNMPMCRC = pMX
Stage 0
TNMPTCRC = pTis TNMPNCRC = pNX TNMPMCRC = pMX
TNMPTCRC = pT0 TNMPNCRC = pN0 TNMPMCRC = pMX
TNMPTCRC = pTis TNMPNCRC = pNX TNMPMCRC = pM0
TNMPTCRC = pT0 TNMPNCRC = pN0 TNMPMCRC = pM0
Stage I
TNMPTCRC = pT1 TNMPNCRC = pN0 TNMPMCRC = pMX
TNMPTCRC = pT2 TNMPNCRC = pN0 TNMPMCRC = pMX
TNMPTCRC = pT1 TNMPNCRC = pN0 TNMPMCRC = pM0
TNMPTCRC = pT2 TNMPNCRC = pN0 TNMPMCRC = pM0
Stage IIA
TNMPTCRC = pT3 TNMPNCRC = pN0 TNMPMCRC = pMX
TNMPTCRC = pT3 TNMPNCRC = pN0 TNMPMCRC = pM0
Stage IIB
TNMPTCRC = pT4a TNMPNCRC = pN0 TNMPMCRC = pMX
TNMPTCRC = pT4a TNMPNCRC = pN0 TNMPMCRC = pM0
Stage IIC
TNMPTCRC = pT4b TNMPNCRC = pN0 TNMPMCRC = pMX
TNMPTCRC = pT4b TNMPNCRC = pN0 TNMPMCRC = pM0
Stage IIIA
TNMPTCRC = pT1 TNMPNCRC = pN1 TNMPMCRC = pMX
TNMPTCRC = pT1 TNMPNCRC = pN1a TNMPMCRC = pMX
TNMPTCRC = pT1 TNMPNCRC = pN1b TNMPMCRC = pMX
TNMPTCRC = pT2 TNMPNCRC = pN1 TNMPMCRC = pMX
TNMPTCRC = pT2 TNMPNCRC = pN1a TNMPMCRC = pMX
TNMPTCRC = pT2 TNMPNCRC = pN1b TNMPMCRC = pMX
TNMPTCRC = pT1 TNMPNCRC = pN1c TNMPMCRC = pMX
TNMPTCRC = pT2 TNMPNCRC = pN1c TNMPMCRC = pMX
TNMPTCRC = pT1 TNMPNCRC = pN2a TNMPMCRC = pMX
TNMPTCRC = pT1 TNMPNCRC = pN1 TNMPMCRC = pM0
TNMPTCRC = pT1 TNMPNCRC = pN1a TNMPMCRC = pM0
TNMPTCRC = pT1 TNMPNCRC = pN1b TNMPMCRC = pM0
TNMPTCRC = pT2 TNMPNCRC = pN1 TNMPMCRC = pM0
TNMPTCRC = pT2 TNMPNCRC = pN1a TNMPMCRC = pM0
TNMPTCRC = pT2 TNMPNCRC = pN1b TNMPMCRC = pM0
TNMPTCRC = pT1 TNMPNCRC = pN1c TNMPMCRC = pM0
TNMPTCRC = pT2 TNMPNCRC = pN1c TNMPMCRC = pM0
TNMPTCRC = pT1 TNMPNCRC = pN2a TNMPMCRC = pM0
Stage IIIB
TNMPTCRC = pT3 TNMPNCRC = pN1 TNMPMCRC = pMX
TNMPTCRC = pT3 TNMPNCRC = pN1a TNMPMCRC = pMX
TNMPTCRC = pT3 TNMPNCRC = pN1b TNMPMCRC = pMX
TNMPTCRC = pT3 TNMPNCRC = pN1c TNMPMCRC = pMX
TNMPTCRC = pT4a TNMPNCRC = pN1 TNMPMCRC = pMX
TNMPTCRC = pT4a TNMPNCRC = pN1a TNMPMCRC = pMX
TNMPTCRC = pT4a TNMPNCRC = pN1b TNMPMCRC = pMX
TNMPTCRC = pT4a TNMPNCRC = pN1c TNMPMCRC = pMX
TNMPTCRC = pT2 TNMPNCRC = pN2a TNMPMCRC = pMX
TNMPTCRC = pT3 TNMPNCRC = pN2a TNMPMCRC = pMX
TNMPTCRC = pT1 TNMPNCRC = pN2b TNMPMCRC = pMX
TNMPTCRC = pT2 TNMPNCRC = pN2b TNMPMCRC = pMX
TNMPTCRC = pT3 TNMPNCRC = pN1 TNMPMCRC = pM0
TNMPTCRC = pT3 TNMPNCRC = pN1a TNMPMCRC = pM0
TNMPTCRC = pT3 TNMPNCRC = pN1b TNMPMCRC = pM0
TNMPTCRC = pT3 TNMPNCRC = pN1c TNMPMCRC = pM0
TNMPTCRC = pT4a TNMPNCRC = pN1 TNMPMCRC = pM0
TNMPTCRC = pT4a TNMPNCRC = pN1a TNMPMCRC = pM0
TNMPTCRC = pT4a TNMPNCRC = pN1b TNMPMCRC = pM0
TNMPTCRC = pT4a TNMPNCRC = pN1c TNMPMCRC = pM0
TNMPTCRC = pT2 TNMPNCRC = pN2a TNMPMCRC = pM0
TNMPTCRC = pT3 TNMPNCRC = pN2a TNMPMCRC = pM0
TNMPTCRC = pT1 TNMPNCRC = pN2b TNMPMCRC = pM0
TNMPTCRC = pT2 TNMPNCRC = pN2b TNMPMCRC = pM0
Stage IIIC
TNMPTCRC = pT4a TNMPNCRC = pN2a TNMPMCRC = pMX
TNMPTCRC = pT3 TNMPNCRC = pN2b TNMPMCRC = pMX
TNMPTCRC = pT4a TNMPNCRC = pN2b TNMPMCRC = pMX
TNMPTCRC = pT4b TNMPNCRC = pN1 TNMPMCRC = pMX
TNMPTCRC = pT4b TNMPNCRC = pN1a TNMPMCRC = pMX
TNMPTCRC = pT4b TNMPNCRC = pN1b TNMPMCRC = pMX
TNMPTCRC = pT4b TNMPNCRC = pN2 TNMPMCRC = pMX
TNMPTCRC = pT4b TNMPNCRC = pN2a TNMPMCRC = pMX
TNMPTCRC = pT4b TNMPNCRC = pN2b TNMPMCRC = pMX
TNMPTCRC = pT4a TNMPNCRC = pN2a TNMPMCRC = pM0
TNMPTCRC = pT3 TNMPNCRC = pN2b TNMPMCRC = pM0
TNMPTCRC = pT4a TNMPNCRC = pN2b TNMPMCRC = pM0
TNMPTCRC = pT4b TNMPNCRC = pN1 TNMPMCRC = pM0
TNMPTCRC = pT4b TNMPNCRC = pN1a TNMPMCRC = pM0
TNMPTCRC = pT4b TNMPNCRC = pN1b TNMPMCRC = pM0
TNMPTCRC = pT4b TNMPNCRC = pN2 TNMPMCRC = pM0
TNMPTCRC = pT4b TNMPNCRC = pN2a TNMPMCRC = pM0
TNMPTCRC = pT4b TNMPNCRC = pN2b TNMPMCRC = pM0
Stage IV
TNMPTCRC = * TNMPNCRC = * TNMPMCRC = pM1
Stage IVA
TNMPTCRC = * TNMPNCRC = * TNMPMCRC = pM1a
Stage IVB
TNMPTCRC = * TNMPNCRC = * TNMPMCRC = pM1b
Stage IVC
TNMPTCRC = * TNMPNCRC = * TNMPMCRC = pM1c
"""

# force build
bc_cancer_stage_spec = """Stage Unknown
TNMPT = pTX TNMPN = pNX TNMPM = pMX
Stage 0
TNMPT = pTisSPACE(DCIS) TNMPN = pN0 TNMPM = pMX
TNMPT = pTisSPACE(DCIS) TNMPN = pN0 TNMPM = pM0
Stage IA
TNMPT = pT1 TNMPN = pN0 TNMPM = pMX
TNMPT = pT1 TNMPN = pN0 TNMPM = pM0
Stage IIA
TNMPT = pT0 TNMPN = pN1 TNMPM = pMX
TNMPT = pT0 TNMPN = pN1 TNMPM = pM0
TNMPT = pT1 TNMPN = pN1 TNMPM = pMX
TNMPT = pT1 TNMPN = pN1 TNMPM = pM0
TNMPT = pT2 TNMPN = pN0 TNMPM = pMX
TNMPT = pT2 TNMPN = pN0 TNMPM = pM0
Stage IIB
TNMPT = pT2 TNMPN = pN1 TNMPM = pMX
TNMPT = pT2 TNMPN = pN1 TNMPM = pM0
TNMPT = pT3 TNMPN = pN0 TNMPM = pMX
TNMPT = pT3 TNMPN = pN0 TNMPM = pM0
Stage IIIA
TNMPT = pT0 TNMPN = pN2 TNMPM = pMX
TNMPT = pT0 TNMPN = pN2 TNMPM = pM0
TNMPT = pT1 TNMPN = pN2 TNMPM = pMX
TNMPT = pT1 TNMPN = pN2 TNMPM = pM0
TNMPT = pT2 TNMPN = pN2 TNMPM = pMX
TNMPT = pT2 TNMPN = pN2 TNMPM = pM0
TNMPT = pT3 TNMPN = pN1 TNMPM = pMX
TNMPT = pT3 TNMPN = pN1 TNMPM = pM0
TNMPT = pT3 TNMPN = pN2 TNMPM = pMX
TNMPT = pT3 TNMPN = pN2 TNMPM = pM0
Stage IIIB
TNMPT = T4 TNMPN = pN0 TNMPM = pMX
TNMPT = T4 TNMPN = pN0 TNMPM = pM0
TNMPT = T4 TNMPN = pN1 TNMPM = pMX
TNMPT = T4 TNMPN = pN1 TNMPM = pM0
TNMPT = T4 TNMPN = pN2 TNMPM = pMX
TNMPT = T4 TNMPN = pN2 TNMPM = pM0
Stage IIIC
TNMPT = pTX TNMPN = pN3 TNMPM = pMX
TNMPT = pTX TNMPN = pN3 TNMPM = pM0
TNMPT = pT0 TNMPN = pN3 TNMPM = pMX
TNMPT = pT0 TNMPN = pN3 TNMPM = pM0
TNMPT = pT1 TNMPN = pN3 TNMPM = pMX
TNMPT = pT1 TNMPN = pN3 TNMPM = pM0
TNMPT = pT2 TNMPN = pN3 TNMPM = pMX
TNMPT = pT2 TNMPN = pN3 TNMPM = pM0
TNMPT = pT3 TNMPN = pN3 TNMPM = pMX
TNMPT = pT3 TNMPN = pN3 TNMPM = pM0
TNMPT = T4 TNMPN = pN3 TNMPM = pMX
TNMPT = T4 TNMPN = pN3 TNMPM = pM0
Stage IV
TNMPT = * TNMPN = * TNMPM = pM1
"""

lc_cancer_stage_spec = """Stage Occult carcinoma
TNMPTLC = Tx TNMPNLC = N0 TNMPMLC = M0
Stage 0
TNMPTLC = Tis TNMPNLC = N0 TNMPMLC = M0
Stage IA1
TNMPTLC = T1mi TNMPNLC = N0 TNMPMLC = M0
TNMPTLC = T1a TNMPNLC = N0 TNMPMLC = M0
Stage IA2
TNMPTLC = T1b TNMPNLC = N0 TNMPMLC = M0
Stage IA3
TNMPTLC = T1c TNMPNLC = N0 TNMPMLC = M0
Stage IB
TNMPTLC = T2a TNMPNLC = N0 TNMPMLC = M0
Stage IIA
TNMPTLC = T2b TNMPNLC = N0 TNMPMLC = M0
Stage IIB
TNMPTLC = T1a TNMPNLC = N1a TNMPMLC = M0
TNMPTLC = T1a TNMPNLC = N1b TNMPMLC = M0
TNMPTLC = T1b TNMPNLC = N1a TNMPMLC = M0
TNMPTLC = T1b TNMPNLC = N1b TNMPMLC = M0
TNMPTLC = T1c TNMPNLC = N1a TNMPMLC = M0
TNMPTLC = T1c TNMPNLC = N1b TNMPMLC = M0
TNMPTLC = T2a TNMPNLC = N1a TNMPMLC = M0
TNMPTLC = T2a TNMPNLC = N1b TNMPMLC = M0
TNMPTLC = T2b TNMPNLC = N1a TNMPMLC = M0
TNMPTLC = T2b TNMPNLC = N1b TNMPMLC = M0
TNMPTLC = T3 TNMPNLC = N0 TNMPMLC = M0
Stage IIIA
TNMPTLC = T1a TNMPNLC = N2a1 TNMPMLC = M0
TNMPTLC = T1a TNMPNLC = N2a2 TNMPMLC = M0
TNMPTLC = T1a TNMPNLC = N2b TNMPMLC = M0
TNMPTLC = T1b TNMPNLC = N2a1 TNMPMLC = M0
TNMPTLC = T1b TNMPNLC = N2a2 TNMPMLC = M0
TNMPTLC = T1b TNMPNLC = N2b TNMPMLC = M0
TNMPTLC = T1c TNMPNLC = N2a1 TNMPMLC = M0
TNMPTLC = T1c TNMPNLC = N2a2 TNMPMLC = M0
TNMPTLC = T1c TNMPNLC = N2b TNMPMLC = M0
TNMPTLC = T2a TNMPNLC = N2a1 TNMPMLC = M0
TNMPTLC = T2a TNMPNLC = N2a2 TNMPMLC = M0
TNMPTLC = T2a TNMPNLC = N2b TNMPMLC = M0
TNMPTLC = T2b TNMPNLC = N2a1 TNMPMLC = M0
TNMPTLC = T2b TNMPNLC = N2a2 TNMPMLC = M0
TNMPTLC = T2b TNMPNLC = N2b TNMPMLC = M0
TNMPTLC = T3 TNMPNLC = N1a TNMPMLC = M0
TNMPTLC = T3 TNMPNLC = N1b TNMPMLC = M0
TNMPTLC = T4 TNMPNLC = N0 TNMPMLC = M0
TNMPTLC = T4 TNMPNLC = N1a TNMPMLC = M0
TNMPTLC = T4 TNMPNLC = N1b TNMPMLC = M0
Stage IIIB
TNMPTLC = T1a TNMPNLC = N3 TNMPMLC = M0
TNMPTLC = T1b TNMPNLC = N3 TNMPMLC = M0
TNMPTLC = T1c TNMPNLC = N3 TNMPMLC = M0
TNMPTLC = T2a TNMPNLC = N3 TNMPMLC = M0
TNMPTLC = T2b TNMPNLC = N3 TNMPMLC = M0
TNMPTLC = T3 TNMPNLC = N2a1 TNMPMLC = M0
TNMPTLC = T3 TNMPNLC = N2a2 TNMPMLC = M0
TNMPTLC = T3 TNMPNLC = N2b TNMPMLC = M0
TNMPTLC = T4 TNMPNLC = N2a1 TNMPMLC = M0
TNMPTLC = T4 TNMPNLC = N2a2 TNMPMLC = M0
TNMPTLC = T4 TNMPNLC = N2b TNMPMLC = M0
Stage IIIC
TNMPTLC = T3 TNMPNLC = N3 TNMPMLC = M0
TNMPTLC = T4 TNMPNLC = N3 TNMPMLC = M0
Stage IVA
TNMPTLC = * TNMPNLC = * TNMPMLC = M1a
TNMPTLC = * TNMPNLC = * TNMPMLC = M1b
Stage IVB
TNMPTLC = * TNMPNLC = * TNMPMLC = M1c
"""

ov_cancer_stage_spec = ""


def get_crc_clinical_cancer_stage_spec():
    return """Stage 0
           TNMCTCRC = cTis TNMCNCRC = cNX TNMCMCRC = cMX
           TNMCTCRC = cTis TNMCNCRC = cNX TNMCMCRC = cM0
           TNMCTCRC = cT0 TNMCNCRC = cN0 TNMCMCRC = cMX
           TNMCTCRC = cT0 TNMCNCRC = cN0 TNMCMCRC = cM0
           Stage I
           TNMCTCRC = cT1 TNMCNCRC = cN0 TNMCMCRC = cMX
           TNMCTCRC = cT1 TNMCNCRC = cN0 TNMCMCRC = cM0
           TNMCTCRC = cT2 TNMCNCRC = cN0 TNMCMCRC = cMX
           TNMCTCRC = cT2 TNMCNCRC = cN0 TNMCMCRC = cM0
           Stage IIA
           TNMCTCRC = cT3 TNMCNCRC = cN0 TNMCMCRC = cMX
           TNMCTCRC = cT3 TNMCNCRC = cN0 TNMCMCRC = cM0
           Stage IIB
           TNMCTCRC = cT4a TNMCNCRC = cN0 TNMCMCRC = cMX
           TNMCTCRC = cT4a TNMCNCRC = cN0 TNMCMCRC = cM0
           Stage IIC
           TNMCTCRC = cT4b TNMCNCRC = cN0 TNMCMCRC = cMX
           TNMCTCRC = cT4b TNMCNCRC = cN0 TNMCMCRC = cM0
           Stage IIIA
           TNMCTCRC = cT1 TNMCNCRC = cN1 TNMCMCRC = cMX
           TNMCTCRC = cT1 TNMCNCRC = cN1 TNMCMCRC = cM0
           TNMCTCRC = cT2 TNMCNCRC = cN1 TNMCMCRC = cMX
           TNMCTCRC = cT2 TNMCNCRC = cN1 TNMCMCRC = cM0
           TNMCTCRC = cT1 TNMCNCRC = cN1c TNMCMCRC = cMX
           TNMCTCRC = cT1 TNMCNCRC = cN1c TNMCMCRC = cM0
           TNMCTCRC = cT2 TNMCNCRC = cN1c TNMCMCRC = cMX
           TNMCTCRC = cT2 TNMCNCRC = cN1c TNMCMCRC = cM0
           TNMCTCRC = cT1 TNMCNCRC = cN2a TNMCMCRC = cMX
           TNMCTCRC = cT1 TNMCNCRC = cN2a TNMCMCRC = cM0
           Stage IIIB
           TNMCTCRC = cT3 TNMCNCRC = cN1 TNMCMCRC = cMX
           TNMCTCRC = cT3 TNMCNCRC = cN1 TNMCMCRC = cM0
           TNMCTCRC = cT3 TNMCNCRC = cN1c TNMCMCRC = cMX
           TNMCTCRC = cT3 TNMCNCRC = cN1c TNMCMCRC = cM0
           TNMCTCRC = cT4a TNMCNCRC = cN1 TNMCMCRC = cMX
           TNMCTCRC = cT4a TNMCNCRC = cN1 TNMCMCRC = cM0
           TNMCTCRC = cT4a TNMCNCRC = cN1c TNMCMCRC = cMX
           TNMCTCRC = cT4a TNMCNCRC = cN1c TNMCMCRC = cM0
           TNMCTCRC = cT2 TNMCNCRC = cN2a TNMCMCRC = cMX
           TNMCTCRC = cT2 TNMCNCRC = cN2a TNMCMCRC = cM0
           TNMCTCRC = cT3 TNMCNCRC = cN2a TNMCMCRC = cMX
           TNMCTCRC = cT3 TNMCNCRC = cN2a TNMCMCRC = cM0
           TNMCTCRC = cT1 TNMCNCRC = cN2b TNMCMCRC = cMX
           TNMCTCRC = cT1 TNMCNCRC = cN2b TNMCMCRC = cM0
           TNMCTCRC = cT2 TNMCNCRC = cN2b TNMCMCRC = cMX
           TNMCTCRC = cT2 TNMCNCRC = cN2b TNMCMCRC = cM0
           Stage IIIC
           TNMCTCRC = cT4a TNMCNCRC = cN2a TNMCMCRC = cMX
           TNMCTCRC = cT4a TNMCNCRC = cN2a TNMCMCRC = cM0
           TNMCTCRC = cT3 TNMCNCRC = cN2b TNMCMCRC = cMX
           TNMCTCRC = cT3 TNMCNCRC = cN2b TNMCMCRC = cM0
           TNMCTCRC = cT4a TNMCNCRC = cN2b TNMCMCRC = cMX
           TNMCTCRC = cT4a TNMCNCRC = cN2b TNMCMCRC = cM0
           TNMCTCRC = cT4b TNMCNCRC = cN1 TNMCMCRC = cMX
           TNMCTCRC = cT4b TNMCNCRC = cN1 TNMCMCRC = cM0
           TNMCTCRC = cT4b TNMCNCRC = cN2 TNMCMCRC = cMX
           TNMCTCRC = cT4b TNMCNCRC = cN2 TNMCMCRC = cM0
           Stage IVA
           TNMCTCRC = cT* TNMCNCRC = cN* TNMCMCRC = cM1a
           Stage IVB
           TNMCTCRC = cT* TNMCNCRC = cN* TNMCMCRC = cM1b
           Stage IVC
           TNMCTCRC = cT* TNMCNCRC = cN* TNMCMCRC = cM1c
           """


def lc_clinical_calcs():
    return """
    """


class RuleParser:
    def __init__(self, spec):
        self.spec = spec


class CancerStageEvaluator:
    def __init__(self, rules_dict=None, spec=None, cde_prefix=None):
        self.cde_prefix = cde_prefix
        self.pattern = "*"
        assert (self.cde_prefix is not None, "cde_prefix must not be None")
        logger.debug("initialising canver stage evaluator")
        if rules_dict is not None:
            self.rules_dict = rules_dict
        else:
            self.rules_dict = self.parse_spec(spec)

        for key in sorted(self.rules_dict.keys()):
            logger.debug("******************************")
            logger.debug(f"Rules for {key}:")
            logger.debug(f"{self.rules_dict[key]}")
            logger.debug("******************************")

        self.cache = {}

    def replace_space(self, s):
        if "SPACE" in s:
            return s.replace("SPACE", " ")
        else:
            return s

    def is_possible(self, cde_code, value):
        from rdrf.models.definition.models import CommonDataElement
        try:
            cde_model = CommonDataElement.objects.get(code=cde_code)
        except CommonDataElement.DoesNotExist:
            error_msg = f"rule contains cde {cde_code} which does not exist"
            raise Exception(error_msg)
        value_dicts = cde_model.pv_group.as_dict()["values"]
        possible_values = [d["value"].lower() for d in value_dicts]

        if self.pattern in value:
            pattern_index = value.find(self.pattern)
            if pattern_index == 0:
                return True

            prefix = value[0:pattern_index].lower()
            for possible_value in possible_values:
                if possible_value.startswith(prefix):
                    return True
        else:
            return value.lower() in possible_values

    def parse_spec_output(self, line):
        return line.strip().replace("Stage ", "")

    def is_value(self, token):
        return not any([self.is_cde(token), token in [' ', '=']])

    def is_cde(self, token):
        return token.startswith(self.cde_prefix)

    def parse_spec_inputs(self, line):
        logger.debug(f"parse_spec_inputs line = {line}")
        dicts = []
        tokens = line.split(" ")
        key = None
        value = None

        for token in tokens:
            logger.debug(f"token = {token}")

            if self.is_cde(token):
                logger.debug(f"token is a cde")
                key = token.strip()
                logger.debug(f"key = {key}")
            elif self.is_value(token):
                logger.debug("token is a value")
                value = token.strip()
                value = self.replace_space(value)
                if key and not self.is_possible(key, value):
                    raise Exception(f"impossible value in rule: cde={key} value={value}")
                logger.debug(f"value = {value}")
            else:
                logger.debug(f"unknown token: {token}")
            if key and value:
                dicts.append({"cde": key, "value": value})
                key = None
                value = None

        return dicts

    def parse_spec(self, spec: str):
        stage = None
        rules_dict = {}

        for line in spec.split("\n"):
            line = line.strip()
            logger.debug(f"parsing line: {line}")
            if line.startswith("Stage"):
                logger.debug("is a stage!")
                stage = self.parse_spec_output(line)
                logger.debug(f"parse stage = {stage}")
                rules_dict[stage] = []
            else:
                logger.debug("is not a stage")
                dicts = self.parse_spec_inputs(line)
                logger.debug(f"parsed dicts = {dicts}")
                if dicts:
                    rules_dict[stage].append(dicts)

        return rules_dict

    def parse_test_spec(self, spec: str) -> list:
        input_output_pairs = []
        output_index = 1
        inputs_index = 0

        def is_valid(pair):
            output = pair[output_index]
            input_dict = pair[inputs_index]
            if input_dict:
                if output:
                    return True

        for line in spec.split("\n"):
            print(line)
            line = line.strip()
            if line.startswith("Stage"):
                pair = [None, None]
                stage = self.parse_spec_output(line)
                pair[output_index] = stage

            else:
                inputs_dict = {}
                tokens = line.split(" ")
                key = None
                value = None
                for token in tokens:
                    if self.is_cde(token):
                        key = token.strip()
                    elif self.is_value(token):
                        value = token.strip()
                        value = self.replace_space(value)
                    if all([key, value]):
                        inputs_dict[key] = value

                pair[inputs_index] = inputs_dict
                if is_valid(pair):
                    input_output_pairs.append(pair)
                pair = [None, stage]

        return input_output_pairs

    def evaluate(self, patient, context):
        for stage, rules in self.rules_dict.items():
            logger.debug(f"*** checking for cancer stage {stage}")
            if self._evaluate_stage(rules, patient, context):
                logger.debug(f"cancer stage: patient {patient} context {context} stage = {stage} evaluates to true")
                return stage
        logger.debug("No rules matched - stage is set to a blank string")
        return "Unknown"

    def _evaluate_stage(self, rules, patient, context):
        stage_value = any([self._evaluate_conjuncts(patient, context, conjuncts) for conjuncts in rules])
        logger.debug(f"stage_value = {stage_value}")
        return stage_value

    def _evaluate_conjuncts(self, patient, context, conjuncts):
        result = all([self._evaluate_conjunct(patient, context, conjunct) for conjunct in conjuncts])
        logger.debug(f"conjuncts = {conjuncts} evaluates to {result}")
        return result

    def _is_pattern(self, value):
        logger.debug(f"checking whether value {value} is a pattern")
        result = value[-1] == self.pattern
        if result:
            logger.debug(f"{value} IS a pattern")
        else:
            logger.debug(f"{value} IS NOT pattern")

        return result

    def _get_pattern_prefix(self, pattern):
        return pattern[:-1]

    def _evaluate_conjunct(self, patient, context, conjunct):
        logger.debug(f"evaluate conjunct: patient {patient} context {context} conjunct {conjunct}")
        from rdrf.models.definition.models import CommonDataElement
        cde_code = conjunct["cde"]
        logger.debug(f"cde code = {cde_code}")
        try:
            cde_model = CommonDataElement.objects.get(code=cde_code)
        except CommonDataElement.DoesNotExist:
            logger.error(f"cannot find cde {cde_code}")
            return False
        rule_display_value = conjunct["value"]
        is_pattern = self._is_pattern(rule_display_value)

        if is_pattern:
            prefix = self._get_pattern_prefix(rule_display_value)
        else:
            prefix = None

        patient_db_value = self._get_patient_value(patient, context, cde_code)
        patient_display_value = cde_model.get_display_value(patient_db_value)

        logger.debug(f"patient db value = {patient_db_value} display value = {patient_display_value}")

        if not is_pattern:
            logger.debug("not a pattern")
            result = patient_display_value.lower() == rule_display_value.lower()
        else:
            logger.debug("pattern found")
            result = patient_display_value.startswith(prefix)

        logger.debug(f"{cde_code} rule {rule_display_value} patient {patient_display_value} result: {result}")
        return result

    def _get_patient_value(self, patient, context, cde_code):
        pv = context[cde_code]  # ??
        logger.debug(f"patient value of {cde_code} is {pv}")
        return pv

    def _get_db_value(self, cde_code, display_value):
        from rdrf.models.definition.models import CommonDataElement
        cde_model = CommonDataElement.objects.get(code=cde_code)
        if cde_model.pv_group:
            d = cde_model.pv_group.as_dict()
            for value_dict in d["values"]:
                if value_dict["value"] == display_value:
                    return value_dict["code"]  # what gets stored in db


def CRCCANCERSTAGE(patient, context):
    logger.info("in cdecrc cancer stage")
    context = fill_missing_input(context, 'CRCCANCERSTAGE_inputs')
    evaluator = CancerStageEvaluator(spec=crc_cancer_stage_spec, cde_prefix="TNMP")
    return evaluator.evaluate(patient, context)


def CRCCANCERSTAGE_inputs():
    return ['TNMPTCRC', 'TNMPNCRC', 'TNMPMCRC']


def CRCCLINICALCANCERSTAGE(patient, context):
    logger.info("in cde crc clinical cancer stage")
    context = fill_missing_input(context, 'CRCCLINICALCANCERSTAGE_inputs')
    spec = get_crc_clinical_cancer_stage_spec()
    evaluator = CancerStageEvaluator(spec=spec, cde_prefix="TNMC")
    return evaluator.evaluate(patient, context)


def CRCCLINICALCANCERSTAGE_inputs():
    return ['TNMCTCRC', 'TNMCNCRC', 'TNMCMCRC']


def BCCANCERSTAGE(patient, context):
    logger.debug(f"calculating BCCANCERSTAGE: patient = {patient} context = {context}")
    context = fill_missing_input(context, 'BCCANCERSTAGE_inputs')
    evaluator = CancerStageEvaluator(spec=bc_cancer_stage_spec, cde_prefix="TNMP")
    return evaluator.evaluate(patient, context)


def BCCANCERSTAGE_inputs():
    return ["TNMPT", "TNMPN", "TNMPM"]


def LCCANCERSTAGE(patient, context):
    context = fill_missing_input(context, 'LCCANCERSTAGE_inputs')
    evaluator = CancerStageEvaluator(spec=lc_cancer_stage_spec, cde_prefix="TNMP")
    return evaluator.evaluate(patient, context)


def LCCANCERSTAGE_inputs():
    return ["TNMPTLC", "TNMPNLC", "TNMPMLC"]


def OVCANCERSTAGE(patient, context):
    context = fill_missing_input(context, 'OVCANCERSTAGE_inputs')
    evaluator = CancerStageEvaluator(ov_cancer_stage_spec)
    return evaluator.evaluate(patient, context)


def OVCANCERSTAGE_inputs():
    return []


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

################ BEGINNING OF FHDeathAge ################################


def APMATPlasmicRisk(patient, context):
    context = fill_missing_input(context, 'APMATPlasmicRisk_inputs')

    YES = "fh_yes_no_yes"
    def yes_selected(value): return value == YES

    score = 0
    score += 1 if yes_selected(context["APMATPlateletCountLessThan30"]) else 0
    score += 1 if yes_selected(context["APMATHaemolysisVariable"]) else 0
    score += 1 if yes_selected(context["APMATNoActiveCancer"]) else 0
    score += 1 if yes_selected(context["APMATNoTransplant"]) else 0
    score += 1 if yes_selected(context["APMATMCVLessThan90"]) else 0
    score += 1 if yes_selected(context["APMATINRLessThan1Dot5"]) else 0
    score += 1 if yes_selected(context["APMATCreatinineLessThan2"]) else 0

    return "low risk" if score < 5 else "intermediate risk" if score == 5 else "high risk"


def APMATPlasmicRisk_inputs():
    return ["APMATPlateletCountLessThan30", "APMATHaemolysisVariable", "APMATNoActiveCancer", "APMATNoTransplant",
            "APMATMCVLessThan90", "APMATINRLessThan1Dot5", "APMATCreatinineLessThan2"]

################ END OF FHDeathAge ################################


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


def number_of_days(datestring1, datestring2):
    """
    return number of days between date1 < date2
    """
    logger.debug(f"number_of_days s1=[{datestring1}] s2=[{datestring2}]")
    if datestring1 is None:
        return None
    if datestring2 is None:
        return None
    try:
        date1 = validate_date(datestring1)
    except ParseError:
        return None
    try:
        date2 = validate_date(datestring2)
    except ParseError:
        return None
    delta = date2 - date1
    return delta.days


def date_diff_helper(patient, context, input_func_name, later_cde_code, earlier_cde_code):
    """
    return number of days between two date cdes in registry
    """
    from registry.patients.models import Patient
    from rdrf.models.definition.models import Registry
    patient_id = patient["patient_id"]
    registry_code = patient["registry_code"]
    patient_model = Patient.objects.get(id=patient_id)
    registry_model = Registry.objects.get(code=registry_code)
    across_forms_info = AcrossFormsInfo(registry_model,
                                        patient_model)
    context = fill_missing_input(context, input_func_name, across_forms_info)
    logger.debug(f"calc context after filling missing input = {context}")
    later_date_string = context[later_cde_code]
    earlier_date_string = context[earlier_cde_code]
    r = number_of_days(earlier_date_string, later_date_string)
    if r is None:
        return ""
    else:
        return str(r)


def INITREVINTERVLC(patient, context):
    """
    This calculation involves cdes on other forms, hence
    the AcrossFormsInfo helper object
    """
    from registry.patients.models import Patient
    from rdrf.models.definition.models import Registry
    patient_id = patient["patient_id"]
    registry_code = patient["registry_code"]
    patient_model = Patient.objects.get(id=patient_id)
    registry_model = Registry.objects.get(code=registry_code)
    across_forms_info = AcrossFormsInfo(registry_model,
                                        patient_model)

    context = fill_missing_input(context, 'INITREVINTERVLC_inputs', across_forms_info)
    first_seenlc = context["FIRSTSEENLC"]
    refdatelc = context["REFDATELC"]
    num_days = number_of_days(refdatelc, first_seenlc)
    if num_days is None:
        return ""
    else:
        return str(num_days)


def INITREVINTERVLC_inputs():
    return ['FIRSTSEENLC', 'REFDATELC']


def DXINTERVALLC(patient, context):
    """
    DXINTERVALLC = INCIDENDATELC – FIRSTSEENLC
    """
    return date_diff_helper(patient,
                            context,
                            'DXINTERVALLC_inputs',
                            'INCIDENDATELC',
                            'FIRSTSEENLC')


def DXINTERVALLC_inputs():
    return ['INCIDENDATELC', 'FIRSTSEENLC']


def MXINTERVAL2LC(patient, context):
    """
    MXINTERVAL2LC = MXDATELC – INCIDENDATELC
    """
    return date_diff_helper(patient,
                            context,
                            'MXINTERVAL2LC_inputs',
                            'MXDATELC',
                            'INCIDENDATELC')


def MXINTERVAL2LC_inputs():
    return ['INCIDENDATELC', 'MXDATELC']


def MXINTERVAL1LC(patient, context):
    """
    MXINTERVAL1LC = MXDATELC – REFDATELC
    """
    return date_diff_helper(patient,
                            context,
                            'MXINTERVAL1LC_inputs',
                            'MXDATELC',
                            'REFDATELC')


def MXINTERVAL1LC_inputs():
    return ['REFDATELC', 'MXDATELC']


def SMOKEPACKYEAR(patient, context):
    """
    from AI
    SMOKEPACKYEAR is an integer.
    If SMOKING = 1  SMOKEPACKYEAR = 0
    If SMOKING = 2 then SMOKEPACKYEAR = CIGDAY/20 x (SMOKINGSTOPYEAR – SMOKINGSTARTYEAR)
    If SMOKING = 3 then SMOKEPACKYEAR = CIGDAY/20 x (THIS YEAR – SMOKINGSTARTYEAR)  THIS YEAR is the year in which the data is collected and entered.
    If SMOKING = 999 then  SMOKEPACKYEAR = 999
    deduct abstinence ( 300822 discussion)
    """

    unknown = "999"

    class NoDataException(Exception):
        pass

    def maybe_int(s):
        logger.debug(f"maybe_int value = {s} type = {type(s)}")
        if s == unknown:
            raise NoDataException()
        if s == 999:
            raise NoDataException()
        if s == "":
            raise NoDataException()
        if s is None:
            raise NoDataException()

        try:
            return int(s)
        except:
            raise NoDataException()

    def get_abstinence_years(context):
        ay = context["SMOKABSTINENTYRS"]
        if not ay:
            return 0
        else:
            ay = int(ay)
            if ay == 999:
                raise NoDataException()
            else:
                return ay

    def get_current_year():
        # this will be when the form is saved ..
        return datetime.now().year

    def calc(cigdays, a, b, c):
        value = (float(cigdays) / 20.0) * (b - a - c)
        return str(int(value))

    smoking = context["SMOKING"]

    if smoking == "1":
        return "0"

    if smoking == "2":
        try:
            cigday = maybe_int(context["CIGDAY"])
            smoking_start_year = maybe_int(context["SMOKINGSTARTYEAR"])
            smoking_stop_year = maybe_int(context["SMOKINGSTOPYEAR"])
            abstinence_years = get_abstinence_years(context)
            return calc(cigday, smoking_start_year, smoking_stop_year, abstinence_years)
        except NoDataException:
            return unknown

    if smoking == "3":
        try:
            cigday = maybe_int(context["CIGDAY"])
            smoking_start_year = maybe_int(context["SMOKINGSTARTYEAR"])
            current_year = get_current_year()
            abstinence_years = get_abstinence_years(context)
            return calc(cigday, smoking_start_year, smoking_stop_year, abstinence_years)
        except NoDataException:
            return unknown

    return unknown


def SMOKEPACKYEAR_inputs():
    return ["CIGDAY", "SMOKING", "SMOKINGSTARTYEAR", "SMOKINGSTOPYEAR", "SMOKABSTINENTYRS"]
