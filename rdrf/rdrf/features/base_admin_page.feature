Feature: Admin Page and Settings
  As a RDRF registry owner
  I want admin users to have access to admin pages and settings
  In order to do administrative tasks using the Web UI

  Background:
    Given development fixtures
    Given a registry named "Sample Registry"

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
    And I should see a link to "Explorer"
    And I should see a link to "User Failed Login Log"
    And I should see a link to "User Login Attempts Log"
    And I should see a link to "User Login Log"


  Scenario: Admin user visits Admin Page
    Given I am logged in as admin
    When I click the User Dropdown Menu
    And I click "Admin Page"
    Then I should see a link to "Patient List"
    And I should see a link to "Reports"
    And I should see a link to "Users"
    And I should see a link to "Genes"
    And I should see a link to "Laboratories"
    # these only in design mode (  which is not default anymore)
    #And I should see a link to "Registries"
    #And I should see a link to "Registry Common Data Elements"
    #And I should see a link to "Registry Common Data Elements Policy"
    #And I should see a link to "Registry Consent Sections"
    #And I should see a link to "Registry Consent Values"
    #And I should see a link to "Registry Context Form Groups"
    And I should see a link to "Registry Demographics Fields"
    #And I should see a link to "Registry Forms"
    #And I should see a link to "Registry Permissible Value Groups"
    #And I should see a link to "Registry Permissible Values"
    #And I should see a link to "Registry Sections"
    And I should see a link to "Groups"
    And I should see a link to "Importer"
    And I should see a link to "Explorer"
    And I should see a link to "Demographics Fields"
    And I should see a link to "Next of Kin Relationship"
    And I should see a link to "Email Notifications"
    And I should see a link to "Email Templates"
    And I should see a link to "Email Notifications History"
    And I should see a link to "Working Groups"
    And I should see a link to "States"
