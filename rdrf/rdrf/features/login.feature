Feature: Login

    Scenario: Login successful as admin
        Given I go to "/"
        And I click "Log in"
        Then I log in as "admin" with "admin" password
        Then I should see "Hello admin"
        Then I should see "Rare Disease Registry Framework"
        And I click "Logout"

    Scenario: Login failed as random user
        Given I go to "/"
        And I click "Log in"
        Then I log in as "RaNdOmUsEr" with "1234567890" password expects "Please enter the correct username and password"
        Then I should see "Login failed"
