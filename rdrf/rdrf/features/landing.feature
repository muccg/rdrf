Feature: Landing

    Scenario: Landing main page
        Given I go to "/"
        Then I should see "Rare Disease Registry Framework"

    Scenario: Landing Page login successful as admin
        Given I go to "/"
        And I click "Log in"
        Then I log in as "admin" with "admin" password
        Then I should see "RDRF Dashboard"
        And I click "Log out"
