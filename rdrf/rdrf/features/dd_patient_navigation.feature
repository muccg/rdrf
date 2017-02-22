Feature: Navigate through forms for a patient
  As a RDRF registry owner
  I want curators to be able to navigate through forms containing patient data
  In order to view patient data

  Background:
    Given export "dd.zip"
    Given a registry named "Demyelinating Diseases Registry"
    And a patient named "ABBOTT Abigail"

  Scenario: Curator navigates to patient consents using the menu
    When I am logged in as curator
    And I click "ABBOTT Abigail" on patientlisting
    When I click "Consents" in sidebar
    Then location is "Consents"

  Scenario: Curator navigates to patient diagnosis using the menu
    When I am logged in as curator
    And I click "ABBOTT Abigail" on patientlisting
    When I click "Diagnosis" in sidebar
    Then location is "Diagnosis"

  Scenario: Curator navigates to patient demographics using the menu
    When I am logged in as curator
    And I click "ABBOTT Abigail" on patientlisting
    When I click "Consents" in sidebar
    When I click "Demographics" in sidebar
    Then location is "Demographics"


  Scenario: Curator navigates through patient forms using forward and back buttons
    When I am logged in as curator
    And I navigate to the patient's page

    And I press the navigate forward button
    Then the page header should be "Consents"

    When I press the navigate forward button
    Then the page header should be "Diagnosis"

    When I press the navigate forward button
    Then the page header should be "Demographics"

    When I press the navigate back button
    Then the page header should be "Diagnosis"

    When I press the navigate back button
    Then the page header should be "Consents"

    When I press the navigate back button
    Then the page header should be "Demographics"
