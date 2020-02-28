Feature: Add a patient and add an address
  As an RDRF registry owner
  I want new patients to be added with valid state value in address

  Background:
    Given export "fh.zip"
    Given a registry named "FH Registry"

  Scenario: Curator user adds a new patient
    When I am logged in as curator
    And I click "Menu"
    And I click "Patient List"
    And I press the "Add Patient" button
    And I select "FH Registry" from "Rdrf Registry"
    And I select "fh Fiona Stanley Hospital" from "Centre"
    And I fill in "Family Name" with "Ford"
    And I fill in "Given Names" with "Falcon"
    And I fill in "Date of birth" with "28-02-1999"
    And I select "Male" from "Sex"
    And I click the add button in "Patient Address" section
    And I fill out "Address" textarea in "Patient Address" section "1" with "456 Hammond Street"
    And I fill out "Suburb" in "Patient Address" section "1" with "Perth"
    And I fill out "Postcode" in "Patient Address" section "1" with "6009"
    And I choose "Australia" from "Country" in "Patient Address" section "1"
    And I press the "Save" button
    Then I should see "Patient Address state: This field is required"
