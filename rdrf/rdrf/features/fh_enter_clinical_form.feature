Feature: Enter clinical form.
  Enter some data on clinical form
  
  Background:
    Given site has loaded export xyz
    
  Scenario: Navigate to clinical form from modules drop down
    Given I login as curator
    When I click Module "Main/Clinical Data" for patient "SMITH, John" on patientlisting
    Then location is "Main/Clinical Data"
  
  Scenario: Navigate to clinical form from sidebar
    Given I login as curator
    When I click "SMITH, John" on  patientlisting
    And I click "Clinical Data" in "Main" group in sidebar 
    Then location is "Main/Clinical Data"

  Scenario: Invalid Clinical Form doesn't Save
    Given I login as curator
    When I click Module "Main/Clinical Data" for patient "SMITH, John" on patientlisting
    And I enter "02-08-2016" for  section "" cde "Consent date"
    And I click Save
    Then error message is "Patient John SMITH not saved due to validation errors"
