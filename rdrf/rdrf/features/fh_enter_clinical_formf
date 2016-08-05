Feature: Enter clinical form.
  Enter some data on clinical form
  
  Background:
    Given export "fh_with_data.zip"
  
  Scenario: Navigate to clinical form from modules drop down
    When I am logged in as curator
    When I click Module "Main/Clinical Data" for patient "SMITH, John" on patientlisting
    Then location is "Main/Clinical Data"
  
  Scenario: Navigate to clinical form from sidebar
    When I am logged in as curator
    When I click "SMITH, John" on  patientlisting
    And I click "Clinical Data" in "Main" group in sidebar 
    Then location is "Main/Clinical Data"

  Scenario: Invalid Clinical Form doesn't Save
    When I am logged in as curator
    When I click Module "Main/Clinical Data" for patient "SMITH, John" on patientlisting
    And I enter "02-08-2016" for  section "" cde "Consent date"
    And I click Save
    Then error message is "Patient John SMITH not saved due to validation errors"
