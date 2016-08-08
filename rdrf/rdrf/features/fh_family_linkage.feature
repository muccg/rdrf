Feature: FH Family Linkage Page
  As a user of FH
  I want to be able to view the families of patients
  In order to do cascade screening.
  Background:
    Given export "fh.zip"

  Scenario: User can visit Family Linkage Page
    When I am logged in as curator
    When I click "SMITH, John" on patientlisting
    When I click "Family Linkage" in sidebar
    Then location is "Family Linkage"
    
