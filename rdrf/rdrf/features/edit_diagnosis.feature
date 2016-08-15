Feature: Edit diagnosis for a patient
  As a RDRF registry owner
  I want curators to edit consents for patients
  In order to have a record of what each patient consented to

  Background:
    Given export "dd.zip"
    Given a registry named "Demyelinating Diseases Registry"
    And a patient named "ABBOT, Abigail"
    # And patient "ABBOT, Abigail" having birthday on "31-01-1990"

  Scenario: Curator navigates to patient consents and edits them
    When I am logged in as curator
    And I navigate to the patient's page
    And I click "Diagnosis"

    And I select "PP (Primary progressive)" from "Condition"
    And I select "DD Affected Status 2" from "Affected Status"
    And I select "Family" from "First Suspected By"
    And I fill in "Date of Diagnosis" with "1-2-1991"
    And I check "Family Consent"
    And I press the "Save" button

    Then I should see "Patient Abigail ABBOT saved successfully"

    When I navigate away then back

    Then the progress indicator should be "12%"
    Then option "PP (Primary progressive)" from "Condition" should be selected
    And option "DD Affected Status 2" from "Affected Status" should be selected
    And option "Family" from "First Suspected By" should be selected
    And value of "Date of Diagnosis" should be "1-2-1991"
    And the "Family Consent" checkbox should be checked
    And value of "Age in years at clinical diagnosis" should be "1"
