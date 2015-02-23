Feature: Registry Definition

Scenario: Admin can go to registry import screen
        Given I go to "/"
        And I click "Log in"
        Then I log in as "admin" with "admin" password
	Then I should see "Hello admin"
	Then I click "Admin Page"
        Then I click "Import Registry Definition"
        Then I should see "Please load from file OR paste in the text area"
        And I click "Log out"
