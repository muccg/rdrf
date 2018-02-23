Feature: Date of migration field
  As an OPHG user I want to enter date of migration
  in the demographics form.

  Background:
    Given export "dd.zip"
    Given a registry named "Demyelinating Diseases Registry"
    And a patient named "ABBOTT Abigail"

  Scenario: Curator navigates to patient demographics, fills in date of migration
    When I am logged in as curator
    And I click "ABBOTT Abigail" on patientlisting
    When I click "Consents" in sidebar
    When I click "Demographics" in sidebar
    Then location is "Demographics"
    When I enter value "23-02-1998" for form "Demographics" section "Patients Personal Details" cde "Date of migration"
    And I press the "Save" button
    Then I should see "Patient's details saved successfully"
