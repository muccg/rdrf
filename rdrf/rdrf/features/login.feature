Feature: Login

    Scenario: Login successful as admin
        Given I go to "/admin"
        Then I log in as "admin" with "admin" password
        Then I should see "Welcome, admin"
        Then I should see "Log out"
        And I click "Log out"

    Scenario: Login failed as random user
        Given I go to "/admin"
        Then I log in as "RaNdOmUsEr" with "1234567890" password expects "Please enter the correct username and password for a staff account."
