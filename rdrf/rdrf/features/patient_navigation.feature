Feature: Navigate through forms for a patient
  As a RDRF registry owner
  I want curators to be able to navigate through forms containing patient data
  In order to view patient data

  Background:
    Given export "dd.zip"
    Given a registry named "Demyelinating Diseases Registry"
    # And registry "Demyelinating Diseases Registry" has "Diagnosis" module
    And a patient named "ABBOT, Abigail"
    # And patient "ABBOT, Abigail" has no consents given

  Scenario: Curator navigates to patient consents using the menu
    When I am logged in as curator
    And I navigate to the patient's page
    And I click "Consents"
    Then the page header should be "Consents"

  Scenario: Curator navigates to patient diagnosis using the menu
    When I am logged in as curator
    And I navigate to the patient's page
    And I click "Diagnosis"
    Then the page header should be "Diagnosis"

  Scenario: Curator navigates to patient diagnosis using the menu
    When I am logged in as curator
    And I navigate to the patient's page
    And I click "Consents"
    And I click "Demographics"
    Then the page header should be "Demographics"


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
