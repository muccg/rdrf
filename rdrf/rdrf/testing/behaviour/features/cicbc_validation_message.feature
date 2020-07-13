Feature: General functionality of CIC Breast (ICHOMBC)
  As a user of CIC Breast
  I should be able to see validation error messages

  Background:
    Given export "cicbc.zip"
    Given a registry named "ICHOM Breast Cancer"

  Scenario: Clinical staff logs in
    When I am logged in as clinical
    And I click "SMITH Jane" on patientslisting
    And I click "Baseline PROMS" in sidebar
    And I enter "1001" for text cde "Indicate height in centimetres"
    And I press the "Save" button
    Then error message is "Patient Jane SMITH not saved due to validation errors"
    And I should see validation error message "Value of 1001 for Indicate height in centimetres is more than maximum value 1000"
    And I enter "-46" for text cde "Indicate height in centimetres"
    And I press the "Save" button
    Then error message is "Patient Jane SMITH not saved due to validation errors"
    And I should see validation error message "Value of -46 for Indicate height in centimetres is less than minimum value 0"
