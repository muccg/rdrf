from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

import math


####################### BEGIN OF CDEfhDutchLipidClinicNetwork ###################################

def bad(value):
    print(math.isnan(value))
    return (value is None) or (math.isnan(value))


def patientAgeAtAssessment2(dob, assessmentDate):
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
            # // try adjusted value
            L = float(adjusted)
            if not math.isnan(L):
                return L
            else:
                return None
        except:
            return None


def getScore(context, patient):
    assessmentDate = context["DateOfAssessment"]

    isAdult = patientAgeAtAssessment2(patient["date_of_birth"], datetime.strptime(assessmentDate, '%Y-%m-%d')) >= 18
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

        return score

    def clinicalHistoryScore():
        score = 0

        if (PERS_HIST_COR_HEART == HAS_COR_HEART_DISEASE):
            score += 2

        if (PERS_HIST_CVD == YES):
            score += 1

        return score

    def physicalExaminationScore():
        score = 0

        if (TENDON_XANTHOMA == "y"):
            score += 6

        if (ARCUS_CORNEALIS == "y"):
            score += 4

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
    print(f"RUNNING CDEfhDutchLipidClinicNetwork")

    return str(getScore(context, patient))


################ END OF CDEfhDutchLipidClinicNetwork ################################


################ BEGINNING OF CD00024 ################################

def getFloat(x):
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
    # // for index patients
    L = CDE00024_getLDL(context)
    if bad(L):
        return ""

    def anyrel(context):
        return (context["CDE00003"] == "fh2_y") or (context["CDE00004"] == "fh2_y") or (
                context["FHFamHistTendonXanthoma"] == "fh2_y") or (context["FHFamHistArcusCornealis"] == "fh2_y")

    # //Definite if DNA Analysis is Yes
    # //other wise
    if L > 5.0:
        return "Highly Probable"

    if L >= 4.0 and anyrel(context):
        return "Probable"

    if L >= 4.0:
        return "Possible"

    return "Unlikely"


def catadult(score):
    # // for index patients
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
        # //  AGE         Unlikely   Uncertain  Likely
        [[0, 14], [[-1, 3.099], [3.1, 3.499], [3.5, BIG]]],
        [[15, 24], [[-1, 2.999], [3.0, 3.499], [3.5, BIG]]],
        [[25, 34], [[-1, 3.799], [3.8, 4.599], [4.6, BIG]]],
        [[35, 44], [[-1, 3.999], [4.0, 4.799], [4.8, BIG]]],
        [[45, 54], [[-1, 4.399], [4.4, 5.299], [5.3, BIG]]],
        [[55, 999], [[-1, 4.299], [4.3, 5.299], [5.3, BIG]]]]

    FEMALE_TABLE = [
        # //  AGE         Unlikely   Uncertain  Likely
        [[0, 14], [[-1, 3.399], [3.4, 3.799], [3.8, BIG]]],
        [[15, 24], [[-1, 3.299], [3.3, 3.899], [3.9, BIG]]],
        [[25, 34], [[-1, 3.599], [3.6, 4.299], [4.3, BIG]]],
        [[35, 44], [[-1, 3.699], [3.7, 4.399], [4.4, BIG]]],
        [[45, 54], [[-1, 3.999], [4.0, 4.899], [4.9, BIG]]],
        [[55, 999], [[-1, 4.399], [4.4, 5.299], [5.3, BIG]]]]

    def inRange(value, a, b):
        return (value >= a) and (value <= b)

    def lookupCat(age, score, table):
        cats = ["Unlikely", "Uncertain", "Likely"]
        for i in range(table.length):
            row = table[i]
            ageInterval = row[0]
            ageMin = ageInterval[0]
            ageMax = ageInterval[1]
            if (inRange(age, ageMin, ageMax)):
                catRanges = row[1]
                for j in range(3):
                    range = catRanges[j]
                    rangeMin = range[0]
                    rangeMax = range[1]

                    if (inRange(score, rangeMin, rangeMax)):
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
    dutch_lipid_network_score = float(context["CDEfhDutchLipidClinicNetwork"])
    assessmentDate = datetime.strptime(context["DateOfAssessment"], '%Y-%m-%d')
    isAdult = patientAgeAtAssessment2(patient["date_of_birth"], assessmentDate) >= 18.0
    index = context["CDEIndexOrRelative"] == "fh_is_index"
    relative = context["CDEIndexOrRelative"] == "fh_is_relative"

    if (index):
        if (isAdult):
            return catadult(dutch_lipid_network_score)
        return catchild(context)

    if (relative):
        age = patientAgeAtAssessment2(patient["date_of_birth"], assessmentDate)
        L = CDE00024_getLDL(context)
        sex = patient.sex
        cr = catrelative(sex, age, L)
        return cr


def CDE00024(patient, context):
    print(f"RUNNING CDE00024")
    return str(categorise(context, patient))


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
    print(f"RUNNING LDLCholesterolAdjTreatment")

    # Inputs
    # LDL-cholesterol concentration
    ldl_chol = float(context["CDE00019"])
    # Dosage
    dose = context["PlasmaLipidTreatment"]

    try:
        return str(roundToTwo(ldl_chol * correction_factor(dose)))

    except:
        return ""

################ END OF LDLCholesterolAdjTreatment ################################

################ BEGINNING OF CDEBMI ################################

def CDEBMI(patient, context):
    print(f"RUNNING CDEBMI")


    height = context["CDEHeight"]
    weight = context["CDEWeight"]

    if not height or not weight:
        return "NaN"

    bmi = weight / (height * height)

    return str(roundToTwo(bmi))

################ END OF CDEBMI ################################