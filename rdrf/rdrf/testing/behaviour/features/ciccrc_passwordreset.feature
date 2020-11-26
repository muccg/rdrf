Feature: Follow the password reset worflow in CIC CRC.
  As a user of CIC CRC
  I should be able to use the password reset form without error.

  Background:
    Given export "ciccrc.zip"
    Given a registry named "ICHOM Colorectal Cancer"

  Scenario: User selects the password reset link, enters their email and submits it, then checks that there have been no errors
    Given I try to log in
    When I click "Trouble signing in"
    Then I should be on the password reset page
    When I enter the email "test@test.com"
    And I click the "Send" button
    Then I should be on the email sent page
    And I should see the site with no errors