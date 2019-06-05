import math
from datetime import datetime

####################### BEGIN OF CDEfhDutchLipidClinicNetwork ###################################

def bad(value):
    return  value is None or math.isnan(value)


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

    isAdult = patientAgeAtAssessment2(patient.date_of_birth, datetime.strptime(assessmentDate, '%Y-%m-%d')) >= 18
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
        # console.log("patient is index");
        if isAdult:

            try:
                score = familyHistoryScore() + clinicalHistoryScore() + physicalExaminationScore() + investigationScore()
                return score
            except:
                return ""
        else:
            # console.log("child - score blank");
            # // child  - score not used ( only categorisation )
            return ""

    else:
        if relative:
            # console.log("relative – score blank");
            # // relative  - score not used ( only categorisation )
            return ""

def CDEfhDutchLipidClinicNetwork(patient, context):
    print(f"RUNNING CDEfhDutchLipidClinicNetwork")

    return str(getScore(context, patient))

################ END OF CDEfhDutchLipidClinicNetwork ################################3