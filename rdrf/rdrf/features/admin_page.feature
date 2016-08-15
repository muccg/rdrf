Feature: Admin Page and Settings
  As a RDRF registry owner
  I want admin users to have access to admin pages and settings
  In order to do administrative tasks using the Web UI

  Background:
    Given export "dd.zip"
    Given a registry named "Demyelinating Diseases Registry"

  Scenario: Admin user drop-down has Admin Page item
    Given I am logged in as admin
    When I click the User Dropdown Menu
    Then I should see a link to "Admin Page"

  Scenario: Admin user has Settings in main menu
    Given I am logged in as admin
    When I click the User Dropdown Menu
    Then I should see a link to "Settings"

  Scenario: Curator user drop-down DOES NOT have Admin Page item
    Given I am logged in as curator
    When I click the User Dropdown Menu
    Then I should NOT see a link to "Admin Page"

  Scenario: Curator user DOES NOT Settings in main menu
    Given I am logged in as curator
    Then I should NOT see a link to "Settings"

  Scenario: Admin user opens Settings menu
    Given I am logged in as admin
    When I click "Settings"
    Then I should see a link to "Registries"
    And I should see a link to "Registry Form"
    And I should see a link to "Sections"
    And I should see a link to "Data Elements"
    And I should see a link to "CDE Policy"
    And I should see a link to "Permissible Value Groups"
    And I should see a link to "Permissible Values"
    And I should see a link to "Consent Sections"
    And I should see a link to "Consent Values"
    And I should see a link to "Groups"
    And I should see a link to "Importer"
    And I should see a link to "Explorer"
    And I should see a link to "Demographics Fields"
    And I should see a link to "Next of Kin Relationship"
    And I should see a link to "Registration Profiles"
    And I should see a link to "Email Notifications"
    And I should see a link to "Email Templates"
    And I should see a link to "Email Notifications History"


  Scenario: Admin user visits Admin Page
    Given I am logged in as admin
    When I click the User Dropdown Menu
    And I click "Admin Page"
    Then I should see a link to "Patient List"
    And I should see a link to "Other Clinicians"
    And I should see a link to "Doctors"
    And I should see a link to "Reports"
    And I should see a link to "Users"
    And I should see a link to "Genes"
    And I should see a link to "Laboratories"
    And I should see a link to "Registries"
    And I should see a link to "Registry Form"
    And I should see a link to "Sections"
    And I should see a link to "Data Elements"
    And I should see a link to "CDE Policy"
    And I should see a link to "Permissible Value Groups"
    And I should see a link to "Permissible Values"
    And I should see a link to "Consent Sections"
    And I should see a link to "Consent Values"
    And I should see a link to "Groups"
    And I should see a link to "Importer"
    And I should see a link to "Explorer"
    And I should see a link to "Demographics Fields"
    And I should see a link to "Next of Kin Relationship"
    And I should see a link to "Registration Profiles"
    And I should see a link to "Email Notifications"
    And I should see a link to "Email Templates"
    And I should see a link to "Email Notifications History"
    And I should see a link to "Working Groups"
    And I should see a link to "States"
