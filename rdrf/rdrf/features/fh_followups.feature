Feature: Follow Up forms.
  As a user of FH I want to be able to add
  multiple follow up forms.
  
  Background:
    Given site has loaded export xyz
    
  Scenario: Navigate to Follow Up Form
    Given I login as curator
    When I click "SMITH, John" on patientlisting
    When I click "Add" in "Follow Ups" group in sidebar
    Then location is "Follow Up"

  Scenario: Save Follow Up
    Given I login as curator
    When I click "SMITH, John" on  patientlisting
    And I click "Add" in "Follow Ups" group in sidebar 
    And I enter "02-08-2016" for form FollowUp section FHFollowUp cde DateOfAssessment
    And I click Save
    Then location is "Follow Up/02-08-2016"

  Scenario: Cancel Follow Up
    Given I login as curator
    When I click "SMITH, John" on  patientlisting
    And I click "Add" in "Follow Ups" group in sidebar 
    And I enter "01-08-2016" for form FollowUp section FHFollowUp cde DateOfAssessment
    And I click Cancel
    And I click Leave
    Then location is "Follow Up"
    
  Scenario: Add Two Follow Ups
    Given I login as curator
    When I click "SMITH, John" on  patientlisting
    And I click "Add" in "Follow Ups" group in sidebar 
    And I enter "01-08-2016" for form FollowUp section FHFollowUp cde DateOfAssessment
    And I click Save
    Then location is "Follow Up/01-08-2016"
    When I click "Add" in "Follow Ups" group in sidebar 
    And I enter "02-08-2016" for form FollowUp section FHFollowUp cde DateOfAssessment
    And I click Save
    Then location is "Follow Up/02-08-2016"
 




