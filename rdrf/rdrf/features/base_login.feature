Feature: Login support
  As a RDRF registry owner
  I want to allow different users to log in
  In order to control access to the registry data

  Background:
    Given development fixtures
    Given a user named "admin"
    And a registry named "Sample Registry"
    When I go to the registry "Sample Registry"

  Scenario: Login successful
    When I log in as "admin" with "admin" password
    Then I should be logged in

  Scenario: Login failed as admin with incorrect password
    When I log in as "admin" with "INCORRECT" password
    Then I should be on the login page

  Scenario: Login failed with random user
    When I log in as "randomUser" with "randomPassword" password
    Then I should be on the login page
