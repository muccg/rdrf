Feature: Login

    Scenario: You are on login page
        Given I go to "/admin"
        Then I should see "Rare Disease Registry Framework"
    
    Scenario: Login successful as admin
        Given I go to "/admin"
        Then I log in as "admin" with "admin" password
        Then I should see "Rare Disease Registry Framework"
        And I click "Log out"

    Scenario: Login failed as random user
        Given I go to "/admin"
        Then I log in as "RaNdOmUsEr" with "1234567890" password expects "Please enter the correct username and password"
