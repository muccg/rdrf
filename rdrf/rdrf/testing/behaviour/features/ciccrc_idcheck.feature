Feature: Check CIC IDs in CIC CRC.
  As a user of CIC CRC
  I should be able to determine a patient's CIC ID.

  Background:
    Given export "ciccrc.zip"
    Given a registry named "ICHOM Colorectal Cancer"

  Scenario: Clinical staff logs in, creates a patient, and checks for existence of patient's CIC ID, then searches for the patient by ID and checks for their existence
    Given I am logged in as clinical
    When I add patient name "WARTON Miles" sex "Male" birthdate "09-12-1989"
    And location is "Demographics"
    Then I should see CIC ID for patient

    When I return to patientlisting
    And I search for the patient using the ID
    Then the patient should exist