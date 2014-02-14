Feature: Registry Definition

Scenario: Admin can go to registry import screen
        Given I go to "/"
        And I click "Log in"
        Then I log in as "admin" with "admin" password
        Then I click "Admin"
        Then I click "Import Registry Definition"
        Then I should see "Registry YAML:"
        And I click "Log out"