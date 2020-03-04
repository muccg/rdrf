Feature: Follow Up forms.
  As a user of FH I want to be able to add
  multiple follow up forms.
  
  Background:
    Given export "fh.zip"
    Given a registry named "FH Registry"
    
  Scenario: Navigate to Follow Up Form
    When I am logged in as curator
    When I click "SMITH John" on patientlisting
    And I press "Add" button in "Follow Up" group in sidebar 
    Then location is "Follow Up"

  Scenario: Save Follow Up
    When I am logged in as curator
    When I click "SMITH John" on  patientlisting
    And I press "Add" button in "Follow Up" group in sidebar 
    And I enter value "02-08-2016" for form "Follow Up" section " " cde "Date of assessment"
    And I click radio button value "No" for section "Events" cde "Has the patient had an event since the last visit?"
    And I click the "Save" button
    Then location is "Follow Up/2-8-2016"

  Scenario: Cancel Follow Up
    When I am logged in as curator
    When I click "SMITH John" on  patientlisting
    And I press "Add" button in "Follow Up" group in sidebar 
    And I enter value "02-8-2016" for form "Follow Up" section " " cde "Date of assessment"
    And I click Cancel
    And I accept the alert
    Then location is "Follow Up"
    
  Scenario: Add Two Follow Ups
    When I am logged in as curator
    When I click "SMITH John" on  patientlisting
    And I press "Add" button in "Follow Up" group in sidebar 
    And I enter value "01-08-2016" for form "Follow Up" section " " cde "Date of assessment"
    And I click radio button value "No" for section "Events" cde "Has the patient had an event since the last visit?"
    And I click the "Save" button
    Then location is "Follow Up/1-8-2016"
    And I press "Add" button in "Follow Up" group in sidebar 
    And I enter value "02-08-2016" for form "Follow Up" section " " cde "Date of assessment"
    And I click radio button value "No" for section "Events" cde "Has the patient had an event since the last visit?"
    And I click the "Save" button
    Then location is "Follow Up/2-8-2016"
