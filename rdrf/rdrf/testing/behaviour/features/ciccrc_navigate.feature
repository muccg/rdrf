Feature: Navigate CIC Clinical (ICHOMCRC).
  As a user of CIC Clinical
  I want to be able to navigate the site.

  Background:
    Given export "ciccrc.zip"
    Given a registry named "ICHOM Colorectal Cancer"

  Scenario: Clinical staff checks all pages
    When I am logged in as clinical
    Then location is "Patient List"
    When I click "SMITH John" on patientlisting
    And location is "Demographics"
    Then I click "Consents" in sidebar
    And location is "Consents"
    Then I click "Proms" in sidebar
    And location is "Patient Reported Outcomes"
    And I check the available survey options
    Then I click "Patient Information" in sidebar  
    And location is "Modules/Patient Information"
    Then I click "Baseline PROMS" in sidebar
    And location is "Modules/Baseline PROMS"
    Then I click "Baseline Clinical" in sidebar
    And location is "Modules/Baseline Clinical"
    Then I click "Pathology" in sidebar
    And location is "Modules/Pathology"
    Then I click "Baseline Treatment" in sidebar
    And location is "Modules/Baseline Treatment"
    Then I click "Follow up and Survival" in sidebar
    And location is "Modules/Follow up and Survival"
    Then I click "BCCA - Bi-national Colorectal Cancer Audit" in sidebar
    And location is "Modules/BCCA - Bi-national Colorectal Cancer Audit"

  Scenario: Clinical staff adds patient and checks all pages
    When I am logged in as clinical
    Then location is "Patient List"
    Then I add patient name "WARD Pendleton" sex "Male" birthdate "19-07-1994"
    And location is "Demographics"
    Then I click "Consents" in sidebar
    And location is "Consents"
    Then I click "Proms" in sidebar
    And location is "Patient Reported Outcomes"
    And I check the available survey options
    Then I click "Patient Information" in sidebar  
    And location is "Modules/Patient Information"
    Then I click "Baseline PROMS" in sidebar
    And location is "Modules/Baseline PROMS"
    Then I click "Baseline Clinical" in sidebar
    And location is "Modules/Baseline Clinical"
    Then I click "Pathology" in sidebar
    And location is "Modules/Pathology"
    Then I click "Baseline Treatment" in sidebar
    And location is "Modules/Baseline Treatment"
    Then I click "Follow up and Survival" in sidebar
    And location is "Modules/Follow up and Survival"
    Then I click "BCCA - Bi-national Colorectal Cancer Audit" in sidebar
    And location is "Modules/BCCA - Bi-national Colorectal Cancer Audit"
