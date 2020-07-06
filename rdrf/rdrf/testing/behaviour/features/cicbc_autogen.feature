Feature: Data entry in patient clinical forms of CIC Breast Cancer (ICHOMBC)
  As a user of CIC Breast Cancer
  I should be able to enter patient clinical data
  And the entered data should be saved correctly

  Background:
    Given export "cicbc.zip"
    Given a registry named "ICHOM Breast Cancer"

  Scenario: Clinical staff logs in and adds patient
    When I am logged in as clinical
    Then location is "Patient List"
    And I add patient name "AUTOTEST Annabelle" sex "Female" birthdate "09-02-1986"
    And location is "Demographics"
    When I click "Clinical" in sidebar
    Then location is "Main/Clinical"
    And I enter "Left breast" for cde "Indicate the laterality of breast cancer" of type "radio"
    And I enter "Primary tumour" for cde "Indicate if this is first breast cancer or new cancer on contralateral or ipsilateral breast" of type "radio"
    And I enter "cT2" for cde "Clinical tumor stage" of type "radio"
    And I enter "cN1" for cde "Clinical nodal stage" of type "radio"
    And I enter "pMx" for cde "Clinical distant metastasis" of type "radio"
    And I click the "Save" button
    Then I should see "Patient Annabelle AUTOTEST saved successfully"
    And option "Left breast" for cde "Indicate the laterality of breast cancer" of type "radio" should be selected
    And option "Primary tumour" for cde "Indicate if this is first breast cancer or new cancer on contralateral or ipsilateral breast" of type "radio" should be selected
    And option "cT2" for cde "Clinical tumor stage" of type "radio" should be selected
    And option "cN1" for cde "Clinical nodal stage" of type "radio" should be selected
    And option "pMx" for cde "Clinical distant metastasis" of type "radio" should be selected
    When I click "Pathology" in sidebar
    Then location is "Main/Pathology"
    And I enter "30-06-2020" for cde "Initial date of histological diagnosis" of type "date"
    And I enter "Ductal carcinoma in situ" for cde "Indicate histological type of the tumour (select all that apply)" of type "multiple"
    And I enter "Invasive lobular carcinoma" for cde "Indicate histological type of the tumour (select all that apply)" of type "multiple"
    And I enter "Not tested" for cde "Indicate if the patient carries a genetic mutation predisposing breast cancer" of type "radio"
    And I enter "Grade 3" for cde "Indicate grade of invasive component of tumour" of type "radio"
    And I enter "Intermediate" for cde "Indicate tumour grade of DCIS component of tumour" of type "radio"
    And I enter "20.3" for cde "Indicate size of invasive component of tumour (in mm)" of type "text"
    And I enter "2" for cde "Number of lymph nodes resected" of type "text"
    And I enter "3" for cde "Number of lymph nodes involved" of type "text"
    And I enter "Yes" for cde "Indicate if the estrogen receptor status is positive" of type "radio"
    And I enter "Not performed" for cde "Indicate if the progesterone receptor status is positive" of type "radio"
    And I enter "Positive" for cde "Indicate if the HER2 receptor status is positive" of type "radio"
    And I enter "pTis (Paget)" for cde "Pathological tumor stage" of type "radio"
    And I enter "pN1" for cde "Pathological nodal stage" of type "radio"
    And I enter "pM0" for cde "Pathological distant metastasis" of type "radio"
    And I click the "Save" button
    Then I should see "Patient Annabelle AUTOTEST saved successfully"
    And I should see "30-6-2020" in cde "Initial date of histological diagnosis"
    And option "Ductal carcinoma in situ" for cde "Indicate histological type of the tumour (select all that apply)" of type "multiple" should be selected
    And option "Invasive lobular carcinoma" for cde "Indicate histological type of the tumour (select all that apply)" of type "multiple" should be selected
    And option "Not tested" for cde "Indicate if the patient carries a genetic mutation predisposing breast cancer" of type "radio" should be selected
    And option "Grade 3" for cde "Indicate grade of invasive component of tumour" of type "radio" should be selected
    And option "Intermediate" for cde "Indicate tumour grade of DCIS component of tumour" of type "radio" should be selected
    And option "Yes" for cde "Indicate if the estrogen receptor status is positive" of type "radio" should be selected
    And option "Not performed" for cde "Indicate if the progesterone receptor status is positive" of type "radio" should be selected
    And option "Positive" for cde "Indicate if the HER2 receptor status is positive" of type "radio" should be selected
    And option "pTis (Paget)" for cde "Pathological tumor stage" of type "radio" should be selected
    And option "pN1" for cde "Pathological nodal stage" of type "radio" should be selected
    And option "pM0" for cde "Pathological distant metastasis" of type "radio" should be selected
    When I click "Treatment" in sidebar
    Then location is "Main/Treatment"
    And I enter "Surgery" for cde "Indicate whether the patient received one of the following treatments during the last year" of type "multiple"
    And I enter "Radiotherapy" for cde "Indicate whether the patient received one of the following treatments during the last year" of type "multiple"
    And I enter "Chemotherapy" for cde "Indicate whether the patient received one of the following treatments during the last year" of type "multiple"
    And I enter "Breast conserving surgery (BCS)" for cde "Indicate whether the patient received surgery during the last year" of type "radio"
    And I enter "01-05-2013" for cde "Provide the date of surgery" of type "date"
    And I enter "Sentinel lymph node biopsy" for cde "Indicate whether the patient received surgery to the axilla during the last year" of type "radio"
    And I enter "01-05-2013" for cde "Please provide the date of surgery to the axilla" of type "date"
    And I enter "No" for cde "Indicate whether the patient received axillary clearance due to lymph node involvement after sentinel lymph node biopsy during the last year" of type "radio"
    And I click the "Save" button
    Then I should see "Patient Annabelle AUTOTEST saved successfully"
    And option "Surgery" for cde "Indicate whether the patient received one of the following treatments during the last year" of type "multiple" should be selected
    And option "Radiotherapy" for cde "Indicate whether the patient received one of the following treatments during the last year" of type "multiple" should be selected
    And option "Chemotherapy" for cde "Indicate whether the patient received one of the following treatments during the last year" of type "multiple" should be selected
    And option "Breast conserving surgery (BCS)" for cde "Indicate whether the patient received surgery during the last year" of type "radio" should be selected
    And I should see "1-5-2013" in cde "Provide the date of surgery"
    And option "Sentinel lymph node biopsy" for cde "Indicate whether the patient received surgery to the axilla during the last year" of type "radio" should be selected
    And I should see "1-5-2013" in cde "Please provide the date of surgery to the axilla"
    And option "No" for cde "Indicate whether the patient received axillary clearance due to lymph node involvement after sentinel lymph node biopsy during the last year" of type "radio" should be selected
    When I click "Survival" in sidebar
    Then location is "Main/Survival"
    And I enter "No" for cde "Is there evidence of local, regional or distant recurrence" of type "radio"
    And I enter "Radiological and histological diagnosis" for cde "Recurrence method" of type "radio"
    And I enter "06-08-2013" for cde "Recurrence date" of type "date"
    And I enter "Yes" for cde "Has the patient died" of type "radio"
    And I enter "19-07-1904" for cde "Date of death (if applicable)" of type "date"
    And I enter "No" for cde "Was death attributable to breast cancer" of type "radio"
    And I click the "Save" button
    Then I should see "Patient Annabelle AUTOTEST saved successfully"
    And option "No" for cde "Is there evidence of local, regional or distant recurrence" of type "radio" should be selected
    And option "Radiological and histological diagnosis" for cde "Recurrence method" of type "radio" should be selected
    And I should see "6-8-2013" in cde "Recurrence date"
    And option "Yes" for cde "Has the patient died" of type "radio" should be selected
    And I should see "19-7-1904" in cde "Date of death (if applicable)"
    And option "No" for cde "Was death attributable to breast cancer" of type "radio" should be selected
