Feature: FH feature practice
  As a user of FH
  I want to be able to edit patient data

  Background:
    Given export "fh.zip"
    Given a registry named "FH Registry"

  Scenario: User can edit Clinical Data page but not save with incomplete data
    When I am logged in as curator
    And I search for patient "SMITH John"
    Then I should see a patient link for "SMITH John"
    Then I click "SMITH John" on patientlisting
    Then I click "Clinical Data" in sidebar
    Then location is "Clinical Data"
    When I fill in "Date of assessment" with "02-02-2020"
    And I click the "Save" button
    Then error message is "Patient John SMITH not saved due to validation errors"

  Scenario: Genetic Data save fails, then repaired and saves successfully
    When I am logged in as curator
    And I search for patient "SMITH John"
    And I click "SMITH John" on patientlisting
    And I click "Genetic Data" in sidebar
    Then location is "Genetic Data"
    When I fill in "Genetic test date" with "02-01-2013"
    And I click radio button value "Heterozygous" for section "" cde "Genotype"
    And I press the "Save" button
    Then error message is "Patient John SMITH not saved due to validation errors"
    Then I click radio button value "Yes" for section "Genetic Analysis" cde "Has the patient had a DNA test?"
    And I press the "Save" button
    Then I should see "Patient John SMITH saved successfully"

  Scenario: All required data in clinical data, with no post checks
    When I am logged in as curator
    And I search for patient "SMITH John"
    Then I should see a patient link for "SMITH John"
    Then I click "SMITH John" on patientlisting
    Then I click "Clinical Data" in sidebar
    Then location is "Clinical Data"
    When I fill in "Date of assessment" with "16-08-2020"
    And I select "Yes" from "Family history of hypercholesterolaemia (first-degree adult relative)"
    And I select "No" from "Family history of hypercholesterolaemia (child aged <18 years)"
    And I select "Yes" from "Family history of premature CVD"
    And I select "No" from "Family history of tendon xanthoma (first-degree relative)"
    And I select "No" from "Family history of arcus cornealis prior to 45 years of age (first-degree relative)"
    And I select "Yes" from "Personal history of premature coronary heart disease"
    And I select "No" from "Personal history of premature cerebral or peripheral vascular disease"
    And I select "No" from "Tendon xanthoma"
    And I select "No" from "Arcus cornealis prior to age 45 years"
    And I fill in "Highest UNTREATED LDL-cholesterol concentration, OR" with "5.5"
    And I press the "Save" button
    Then I should see "Patient John SMITH saved successfully"

  Scenario: Entering Medications data, including checkboxes
    When I am logged in as curator
    When I click Module "Main/Medications" for patient "SMITH John" on patientlisting
    Then location is "Medications"
    When I click radio button value "No" for section "Lipid-lowering Medication" cde "Is the patient on lipid-lowering medication?"
    And I enter value "A string including the word cake" for form "Medications" section "Lipid-lowering Medication" cde "If other, enter medication name(s), dose(s) and regime"
    And I check "Thiazide diuretics"
    And I check "ARBs"
    And I check "Other"
    And I enter value "Yes, more cake" for form "Medications" section "Hypertensive Medication" cde "If other, enter medication name(s)"
    And I scroll cde "Is the patient on hypertensive medication?" to the centre of my view
    And I click radio button value "Yes" for section "Hypertensive Medication" cde "Is the patient on hypertensive medication?"
    And I press the "Save" button
    Then I should see "Patient John SMITH saved successfully"
    And the form value of section "Lipid-lowering Medication" cde "If other, enter medication name(s), dose(s) and regime" should be "A string including the word cake"
    And the "Thiazide diuretics" checkbox should be checked
    And the "ARBs" checkbox should be checked
    And the "Other" checkbox should be checked
    And the form value of section "Hypertensive Medication" cde "If other, enter medication name(s)" should be "Yes, more cake"
