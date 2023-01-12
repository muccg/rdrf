Feature: IPRestrict is enabled and working
  As a RDRF registry owner
  I want to retrict access by IP to all or part of the application

  Background:
    Given development fixtures
    Given a registry named "Sample Registry"

  Scenario: Admin user blocks useraudit to localhost
    Given I am logged in as admin
    When I click the User Dropdown Menu
    And I click "Admin Page"
    And I click "IP Restrict Rules"
    Then I should see "Rules"
    And I click "Add"
    And I fill in "Url pattern" with ".*useraudit.*"
    And I select "ALL" from "Ip group"
    And I select "DENY" from "Action"
    And I click the "Save" button
    Then I should see "added successfully"
    Given I reload iprestrict
    When I click "Settings"
    And I click "User Login Log"
    Then I should see "Looks like you don't have access to this page"
