Feature: Admin

    Scenario: Admin interface has working link to Patient Forms
        Given I go to "/admin"
        Then I log in as "curator" with "curator" password
        Then I should see "Welcome, curator"
        And I click "Patients"


    Scenario: Curator DOES NOT see Import Registry link
        Given I go to "/admin"
        Then I log in as "curator" with "curator" password
        Then I should see "Welcome, curator"
        Then I should see "Quick access links"
        Then I should not see "Import Registry Definition"


    Scenario: Admin DOES see Import Registry link
        Given I go to "/admin"
        Then I log in as "admin" with "admin" password
        Then I should see "Welcome, admin"
        Then I should see "Import Registry Definition"
