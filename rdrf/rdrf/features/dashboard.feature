Feature: Dashboard

    Scenario: Dashboard main page
        Given I go to "/dashboard"
        Then I should see "Rare Disease Registry Framework"

    Scenario: Dashboard login successful as admin
        Given I go to "/dashboard"
        Then I log in as "admin" with "admin" password
        Then I should see "Welcome to RDRF admin!"
        And I click "Log out"
