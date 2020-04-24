Feature: Menu options in CIC Clinical (ICHOMCRC).
  As a user of CIC Clinical
  I should be able to see menu elements.

  Background:
    Given export "ciccrc.zip"
    Given a registry named "ICHOM Colorectal Cancer"

  Scenario: Admin logs in
    When I am logged in as admin
    Then the menu "Menu" contains "Consents (ICHOM Colorectal Cancer)"
    And the menu "Menu" contains "Genes"
    And the menu "Menu" contains "Laboratories"
    And the menu "Menu" contains "Patient List"
    And the menu "Menu" contains "Reports"
    And the menu "Menu" contains "Users"
    Then the menu "Settings" contains "Explorer"
    And the menu "Settings" contains "Permissions (ICHOM Colorectal Cancer)"
    And the menu "Settings" contains "User Failed Login Log"
    And the menu "Settings" contains "User Login Attempts Log"
    And the menu "Settings" contains "User Login Log"
    Then the menu "admin" contains "Admin Page"
    And the menu "admin" contains "Change Password"
    And the menu "admin" contains "Enable two-factor auth"
    And the menu "admin" contains "Logout"

  Scenario: Clinical staff logs in
    When I am logged in as clinical
    Then the menu "Menu" contains "Patient List"
    And the menu "clinical" contains "Change Password"
    And the menu "clinical" contains "Enable two-factor auth"
    And the menu "clinical" contains "Logout"
