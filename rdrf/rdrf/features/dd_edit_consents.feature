Feature: Edit consents for a patient
  As a RDRF registry owner
  I want curators to edit consents for patients
  In order to have a record of what each patient consented to

  Background:
    Given export "dd.zip"
    Given a registry named "Demyelinating Diseases Registry"
    And a patient named "ABBOTT Abigail"

  Scenario: Curator navigates to patient consents and edits them
    When I am logged in as curator
    When I click "ABBOTT Abigail" on patientlisting
    When I click "Consents" in sidebar

    And I check "Consent given to store data only while individual is living"
    And I check "Consent given to store data for the duration of the registry"
    And I check "Consent provided by Parent/Guardian only while individual is living"
    And I check "Consent provided by Parent/Guardian for the duration of the registry"
    And I press the "Save" button

    When I navigate away then back

    Then the "Consent given to store data only while individual is living" checkbox should be checked
    And the "Consent given to store data for the duration of the registry" checkbox should be checked
    And the "Consent provided by Parent/Guardian only while individual is living" checkbox should be checked
    And the "Consent provided by Parent/Guardian for the duration of the registry" checkbox should be checked
