Feature: Add a patient
  As a RDRF registry owner
  I want curators to be able to add new patients
  In order to register patients in the registry

  Background:
    Given export "dd.zip"
    Given a registry named "Demyelinating Diseases Registry"

  Scenario: Curator user adds a new patient
    When I am logged in as curator
    And I click "Menu"
    And I click "Patient List"
    And I press the "Add Patient" button
    And I select "Demyelinating Diseases Registry" from "Rdrf Registry"
    And I select "dd WA" from "Centre"
    And I fill in "Family Name" with "Taylor"
    And I fill in "Given Names" with "Tom"
    And I fill in "Date of birth" with "28-02-1999"
    And I select "Male" from "Sex"
    And I press the "Save" button
    Then I should see "Patient added successfully"
    And I should see "TAYLOR Tom"
    And option "Demyelinating Diseases Registry" from "Rdrf Registry" should be selected
    And option "dd WA" from "Centre" should be selected
    And value of "Family Name" should be "TAYLOR"
    And value of "Given Names" should be "Tom"
    And value of "Date of birth" should be "28-02-1999"
    And option "Male" from "Sex" should be selected
