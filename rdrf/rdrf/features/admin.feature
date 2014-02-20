Feature: Admin

    Scenario: Curator does NOT see Rdrf admin objects ( registry definition objects ) in Admin
        Given I go to "/"
        And I click "Log in"
        Then I log in as "curator" with "curator" password
        And I click "Admin"
        Then I should not see "Rdrf"
        And I click "Log out"


    Scenario: Admin DOES see Rdrf admin objects in admin interface
        Given I go to "/"
        And I click "Log in"
        Then I log in as "admin" with "admin" password
        And I click "Admin"
        Then I should see "Rdrf"
        And I click "Log out"


    Scenario: Admin interface has working link back to dashboard
        Given I go to "/"
        And I click "Log in"
        Then I log in as "curator" with "curator" password
        And I click "Admin"
        And I click "Dashboard"
        Then I should see "RDRF Dashboard"



