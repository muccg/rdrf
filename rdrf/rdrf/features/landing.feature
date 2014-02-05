Feature: Landing

    Scenario: Landing main page
        Given I go to "/"
        Then I should see "Rare Disease Registry Framework Landing Page"

    Scenario: Landing Page login successful as admin
        Given I go to "/"
        And I click "Log in"
        Then I log in as "admin" with "admin" password
        Then I should see "Welcome to the RDRF Dashboard admin"
        And I click "Log out"
