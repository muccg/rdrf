Feature: Admin

    Scenario: Admin interface has working link to Patient Forms
        Given I go to "/"
        I accept the alert
        And I click "Log in"
        Then I log in as "curator" with "curator" password
        And I click "Patients"
        Then I should see "Patients"


    Scenario: Curator DOES NOT see Import Registry link
        Given I go to "/"
        And I click "Log in"
        Then I log in as "curator" with "curator" password
        Then I should not see "Import Registry Definition"


    Scenario: Admin DOES see Import Registry link
        Given I go to "/"
        And I click "Log in"
        Then I log in as "admin" with "admin" password
        Then I should see "Import Registry Definition"
