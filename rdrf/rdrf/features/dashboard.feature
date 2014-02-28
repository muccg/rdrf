Feature: Dashboard

    Scenario: Login successful as curator
        Given I go to "/"
        And I click "Log in"
        Then I log in as "curator" with "curator" password
        Then I should see "Rare Disease Registry Framework"


    Scenario: Login failed as random user
        Given I go to "/"
        And I click "Log in"
        Then I log in as "RaNdOmUsEr" with "1234567890" password expects "Please enter the correct username and password"


    Scenario: Logout successful as curator
        Given I go to "/"
        And I click "Log in"
        Then I log in as "curator" with "curator" password
        Then I should see "Rare Disease Registry Framework"
        And I click "Log out"
        Then I should see "Welcome to Rare Disease Registry Framework!"


    Scenario: Curator can go to admin from dashboard
        Given I go to "/"
        And I click "Log in"
        Then I log in as "curator" with "curator" password
        Then I should see "Next of Kin Relationships" # heuristic to tell if we're on the admin page
        And I click "Log out"