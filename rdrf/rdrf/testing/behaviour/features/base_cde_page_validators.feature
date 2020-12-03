Feature: Hiding unneeded validation options on the CDE admin page
  As an owner of a registry on RDRF
  I want administrators to only use the correct CDE validation options
  Depending on the data type of the CDE created

  Background:
    Given export "ciccrc.zip"
    Given a registry named "ICHOM Colorectal Cancer"

  Scenario: Admin user creates new CDE, but does not yet select a data type
    Given I am logged in as admin
    When I go to the Common Data Element admin page
    And I click the Add button
    Then I should be on the CDE editing page
    And I should see the "Pv group" field
    And I should see the "Allow multiple" checkbox
    And I should see the "Max length" field
    And I should see the "Max value" field
    And I should see the "Min value" field
    And I should see the "Pattern" field

  Scenario: Admin user creates new CDE and selects String for the CDE data type
    Given I am logged in as admin
    When I go to the Common Data Element admin page
    And I click the Add button
    Then I should be on the CDE editing page
    When I select "string" from "datatype"
    Then I should see the "Max length" field
    And I should see the "Pattern" field
    And I should NOT see the "Pv group" field
    And I should NOT see the "Allow multiple" checkbox
    And I should NOT see the "Max value" field
    And I should NOT see the "Min value" field

  Scenario: Admin user creates new CDE and selects Integer for the CDE data type
    Given I am logged in as admin
    When I go to the Common Data Element admin page
    And I click the Add button
    Then I should be on the CDE editing page
    When I select "integer" from "datatype"
    Then I should see the "Max value" field
    And I should see the "Min value" field
    And I should NOT see the "Max length" field
    And I should NOT see the "Pv group" field
    And I should NOT see the "Allow multiple" checkbox
    And I should NOT see the "Pattern" field

  Scenario: Admin user creates new CDE and selects Decimal for the CDE data type
    Given I am logged in as admin
    When I go to the Common Data Element admin page
    And I click the Add button
    Then I should be on the CDE editing page
    When I select "float" from "datatype"
    Then I should see the "Max value" field
    And I should see the "Min value" field
    And I should NOT see the "Max length" field
    And I should NOT see the "Pv group" field
    And I should NOT see the "Allow multiple" checkbox
    And I should NOT see the "Pattern" field

  Scenario: Admin user creates new CDE and selects Alpha Numeric for the CDE data type
    Given I am logged in as admin
    When I go to the Common Data Element admin page
    And I click the Add button
    Then I should be on the CDE editing page
    When I select "alphanumeric" from "datatype"
    Then I should see the "Max length" field
    And I should see the "Pattern" field
    And I should NOT see the "Pv group" field
    And I should NOT see the "Allow multiple" checkbox
    And I should NOT see the "Max value" field
    And I should NOT see the "Min value" field

  Scenario: Admin user creates new CDE and selects Date for the CDE data type
    Given I am logged in as admin
    When I go to the Common Data Element admin page
    And I click the Add button
    Then I should be on the CDE editing page
    When I select "date" from "datatype"
    Then I should NOT see the "Pv group" field
    And I should NOT see the "Allow multiple" checkbox
    And I should NOT see the "Max length" field
    And I should NOT see the "Max value" field
    And I should NOT see the "Min value" field
    And I should NOT see the "Pattern" field

  Scenario: Admin user creates new CDE and selects Boolean for the CDE data type
    Given I am logged in as admin
    When I go to the Common Data Element admin page
    And I click the Add button
    Then I should be on the CDE editing page
    When I select "boolean" from "datatype"
    Then I should NOT see the "Pv group" field
    And I should NOT see the "Allow multiple" checkbox
    And I should NOT see the "Max length" field
    And I should NOT see the "Max value" field
    And I should NOT see the "Min value" field
    And I should NOT see the "Pattern" field

  Scenario: Admin user creates new CDE and selects Range for the CDE data type
    Given I am logged in as admin
    When I go to the Common Data Element admin page
    And I click the Add button
    Then I should be on the CDE editing page
    When I select "range" from "datatype"
    Then I should see the "Pv group" field
    And I should see the "Allow multiple" checkbox
    And I should NOT see the "Max length" field
    And I should NOT see the "Max value" field
    And I should NOT see the "Min value" field
    And I should NOT see the "Pattern" field

  Scenario: Admin user creates new CDE and selects Calculated for the CDE data type
    Given I am logged in as admin
    When I go to the Common Data Element admin page
    And I click the Add button
    Then I should be on the CDE editing page
    When I select "calculated" from "datatype"
    Then I should NOT see the "Pv group" field
    And I should NOT see the "Allow multiple" checkbox
    And I should NOT see the "Max length" field
    And I should NOT see the "Max value" field
    And I should NOT see the "Min value" field
    And I should NOT see the "Pattern" field

  Scenario: Admin user creates new CDE and selects File for the CDE data type
    Given I am logged in as admin
    When I go to the Common Data Element admin page
    And I click the Add button
    Then I should be on the CDE editing page
    When I select "file" from "datatype"
    Then I should NOT see the "Pv group" field
    And I should NOT see the "Allow multiple" checkbox
    And I should NOT see the "Max length" field
    And I should NOT see the "Max value" field
    And I should NOT see the "Min value" field
    And I should NOT see the "Pattern" field

#These will be expanded on after initial testing
  #Scenario: Admin user changes the data type of a String CDE with max length and pattern set to Integer, then back
  #Scenario: Admin user changes the data type of an Integer CDE with max value and min value set to String, then back
  #Scenario: Admin user changes the data type of a Range CDE with PV group set and allow multiple checked to another type, then back