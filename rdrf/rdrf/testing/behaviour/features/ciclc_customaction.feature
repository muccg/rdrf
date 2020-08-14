Feature: CIC LC Custom Action menu check
  As a user of CIC Lung
  I should see the Custom Action "Patient Report" in the Menu
  But only on the patient's clinical forms

  Background:
    Given export "ciclc.zip"
    Given a registry named "ICHOM Lung Cancer"

  Scenario: Clinical staff logs in and checks Menu for Patient Report
    When I am logged in as clinical
    And location is "Patient List"
    Then the menu "Menu" DOES NOT contain "Patient Report"
    When I click "SMITH John" on patientslisting
    And location is "Demographics"
    Then the menu "Menu" contains "Patient Report"

