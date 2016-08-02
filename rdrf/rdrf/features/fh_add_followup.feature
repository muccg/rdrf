Feature: Follow Up forms.
  As a user of FH I want to be able to add
  mutliple follow up forms.
  
  Background:
    Given site has loaded export xyz
    
  Scenario: Click Add Follow Up
    Given I login as curator
    When I click "SMITH, John" on patient listing
    When I click "Add" in "Follow Ups" panel
    Then location is "Follow Up"

  Scenario Save Follow Up
    Given I login as curator
    When I click "SMITH, John" on patient listing
    When I click "Add" in "Follow Ups" panel
    When I enter 02-08-2016 for form "FollowUp"/FHFollowUpDateOfAssessment


