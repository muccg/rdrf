Feature: Add a patient and add an address with no country
  As a user of FH
  I want new patients to be added with a valid country value in address

  Background:
    Given export "fh.zip"
    Given a registry named "FH Registry"

  Scenario: Clinical staff attempts to add new patient with no country selected for address
    When I am logged in as curator
    And I click "Menu"
    And I click "Patient List"
    And I press the "Add Patient" button
    And I select "fh Fiona Stanley Hospital" from "Centre"
    And I fill in "Family Name" with "Baston"
    And I fill in "Given Names" with "Billy"
    And I fill in "Date of birth" with "10-09-2002"
    And I select "Male" from "Sex"
    And I click the add button in "Patient Address" section
    And I fill out "Address" textarea in "Patient Address" section "1" with "39 Hercules Close"
    And I fill out "Suburb" in "Patient Address" section "1" with "Perth"
    And I fill out "Postcode" in "Patient Address" section "1" with "6000"
    And I press the "Save" button
    Then I should see an error message saying "Patient Address country: This field is required"