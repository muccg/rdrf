Feature: Landing

    Scenario: Landing main page
        Given I go to "/"
        Then I should see "The following registries are defined on this site"
