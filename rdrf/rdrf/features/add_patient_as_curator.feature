Feature: Add Patient as Curator

Scenario: FH curator only sees FH registry
        Given I go to "/admin"
        When I log in as "fhcurator" with "fhcurator" password
        Then I should see "Welcome, fhcurator"
        And I click "Log out"
        I accept the alert
