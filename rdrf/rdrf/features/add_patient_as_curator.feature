Feature: Add Patient as Curator

Scenario: FH curator only sees FH registry
        Given I go to "/"
        And I click "Log in"
        When I log in as "fhcurator" with "fhcurator" password
        Then I should see "Quick access links"
        When I click "Patients"
        Then I should see "Demographics"
        Given I go to "/admin/patients/patient/add/"
        The "FH Registry (fh)" option from "Rdrf registry" should be selected
        And I click "Log out"
        I accept the alert
