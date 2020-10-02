Feature: Check GUI elements of the Completion Report page in CIC CRC.
  As a user of CIC CRC
  I should be able to see the date boxes and submit button on the Completion Report page.

  Background:
    Given export "ciccrc.zip"
    Given a registry named "ICHOM Colorectal Cancer"
  
  Scenario: Clinical staff logs in, selects Completion Report from Menu, and checks page for date boxes and submit button
    Given I am logged in as clinical
    When I open the drop-down menu
    And I select the custom action "Completion Report"
    Then I should see 2 "date" elements
    And I should see 1 "submit" element