Feature: CDE marks in CIC Clinical (ICHOMCRC).
  As a user of CIC Clinical
  I should see CDEs marked as required
  And I should see CDEs marked as abnormal
  But only if they are actually abnormal

  Background:
    Given export "ciccrc.zip"
    Given a registry named "ICHOM Colorectal Cancer"

  Scenario: Abnormality on Baseline PROMS
    When I am logged in as clinical
    And I click "SMITH John" on patientlisting
    And location is "Demographics"
    Then I click "Baseline PROMS" in sidebar
    And location is "Modules/Baseline PROMS"
    Then the cde "Do you have any trouble taking a long walk?" is NOT marked as abnormal
    And the cde "How would you rate your overall health during the past week?" is NOT marked as abnormal
    And I select radio value "Very much" for cde "Do you have any trouble taking a long walk?"
    And I select "1" from "How would you rate your overall health during the past week?"
    And I press the "Save" button
    Then radio value "Very much" for cde "Do you have any trouble taking a long walk?" should be selected
    And the cde "Do you have any trouble taking a long walk?" is marked as abnormal
    And the cde "How would you rate your overall health during the past week?" is marked as abnormal
    Then I select radio value "Quite a bit" for cde "Do you have any trouble taking a long walk?"
    And I select "2" from "How would you rate your overall health during the past week?"
    And I press the "Save" button
    Then radio value "Quite a bit" for cde "Do you have any trouble taking a long walk?" should be selected
    And the cde "Do you have any trouble taking a long walk?" is marked as abnormal
    Then I select radio value "A little" for cde "Do you have any trouble taking a long walk?"
    And I select "3" from "How would you rate your overall health during the past week?"
    And I press the "Save" button
    Then radio value "A little" for cde "Do you have any trouble taking a long walk?" should be selected
    And the cde "Do you have any trouble taking a long walk?" is NOT marked as abnormal
    And the cde "How would you rate your overall health during the past week?" is NOT marked as abnormal

  Scenario: Required fields on Demographics
    When I am logged in as clinical
    And I click "SMITH John" on patientlisting
    And location is "Demographics"
    Then the cde "Family Name" is marked as required
    And the cde "Given Names" is marked as required
    And the cde "Date of birth" is marked as required
    And the cde "Sex" is marked as required
    And the cde "Living status" is marked as required
    And the cde "Country of birth" is NOT marked as required
    And the cde "Home phone" is NOT marked as required
    And the cde "Mobile phone" is NOT marked as required
    And the cde "Work phone" is NOT marked as required
    And the cde "Email" is NOT marked as required
