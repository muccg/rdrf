Feature: Add a patient and add an address
  As an RDRF registry owner
  I want curators to edit patients with state value changed in address

  Background:
    Given export "fh.zip"
    Given a registry named "FH Registry"

  Scenario: Curator user adds and edits a patient
    When I am logged in as curator
    When I click "Menu"
    And I click "Patient List"
    And I press the "Add Patient" button
    And I select "FH Registry" from "Rdrf Registry"
    And I select "fh Fiona Stanley Hospital" from "Centre"
    And I fill in "Family Name" with "Toyota"
    And I fill in "Given Names" with "Yaris"
    And I fill in "Date of birth" with "28-02-1999"
    And I select "Male" from "Sex"

    And I click the add button in "Patient Address" section
    And I fill out "Address" textarea in "Patient Address" section "1" with "23 Hammond Road"
    And I fill out "Suburb" in "Patient Address" section "1" with "Claremont"
    And I fill out "Postcode" in "Patient Address" section "1" with "6010"
    And I choose "Australia" from "Country" in "Patient Address" section "1"
    And I choose "Australian Capital Territory" from "State" in "Patient Address" section "1"

    And I press the "Save" button

    Then I should see "Patient added successfully"

    And I choose "Victoria" from "State" in "Patient Address" section "1"

    And I press the "Save" button

    Then I should see "Patient's details saved successfully"
