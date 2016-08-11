Feature: Follow Up forms.
  As a user of FH I want to be able to add
  multiple follow up forms.
  
  Background:
    Given export "fh.zip"
    Given a registry named "FH Registry"
    
  Scenario: Navigate to Follow Up Form
    When I am logged in as curator
    When I click "SMITH, John" on patientlisting
    When I click "Add" in "Follow Ups" group in sidebar
    Then location is "Follow Up"

  Scenario: Save Follow Up
    When I am logged in as curator
    When I click "SMITH, John" on  patientlisting
    And I click "Add" in "Follow Ups" group in sidebar 
    And I enter "02-08-2016" for form FollowUp section FHFollowUp cde DateOfAssessment
    And I click Save
    Then location is "Follow Up/02-08-2016"

  Scenario: Cancel Follow Up
    When I am logged in as curator
    When I click "SMITH, John" on  patientlisting
    And I click "Add" in "Follow Ups" group in sidebar 
    And I enter "01-08-2016" for form FollowUp section FHFollowUp cde DateOfAssessment
    And I click Cancel
    And I click Leave
    Then location is "Follow Up"
    
  Scenario: Add Two Follow Ups
    When I am logged in as curator
    When I click "SMITH, John" on  patientlisting
    And I click "Add" in "Follow Ups" group in sidebar 
    And I enter "01-08-2016" for form FollowUp section FHFollowUp cde DateOfAssessment
    And I click Save
    Then location is "Follow Up/01-08-2016"
    When I click "Add" in "Follow Ups" group in sidebar 
    And I enter "02-08-2016" for form FollowUp section FHFollowUp cde DateOfAssessment
    And I click Save
    Then location is "Follow Up/02-08-2016"
 




