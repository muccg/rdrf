Feature: Add Patient as Curator

Scenario: FH curator only sees FH registry
        Given I go to "/"
        And I click "Log in"
        When I log in as "fhcurator" with "fhcurator" password
        Then I should see "Hello fhcurator"
        Given I go to "/admin/patients/patient/add/"
        The "FH Registry (fh)" option from "Rdrf registry" should be selected
        And I click "Logout"
        I accept the alert
