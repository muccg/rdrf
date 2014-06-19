Feature: Add Patient as Admin

Scenario: Admin sees all registries
        Given I go to "/"
        And I click "Log in"
        When I log in as "admin" with "admin" password
        Then I should see "Quick access links"
        When I click "Patients"
        Then I should see "Demographics"
        Given I go to "/admin/patients/patient/add/"
        I should see option "FH Registry (fh)" in selector "Rdrf registry"
        I should see option "SMA (sma)" in selector "Rdrf registry"
        And I click "Log out"
        I accept the alert
