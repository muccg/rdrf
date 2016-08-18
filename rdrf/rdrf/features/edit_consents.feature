Feature: Edit consents for a patient
  As a RDRF registry owner
  I want curators to edit consents for patients
  In order to have a record of what each patient consented to

  Background:
    Given a registry named "Demyelinating Diseases Registry"
    And a patient named "ABBOT, Abigail"
    # And patient "ABBOT, Abigail" having no consents given

  Scenario: Curator navigates to patient consents and edits them
    When I am logged in as curator
    And I navigate to the patient's page
    And I click "Consents"

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
