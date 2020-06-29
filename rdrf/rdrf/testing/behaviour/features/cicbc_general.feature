Feature: General functionality of CIC Breast (ICHOMBC)
  As a user of CIC Breast
  I should be able to see page elements
  And I should be able to interact with the site

  Background:
    Given export "cicbc.zip"
    Given a registry named "ICHOM Breast Cancer"

  Scenario: Clinical staff logs in
    When I am logged in as clinical
    Then location is "Patient List"
    And the menu "Menu" contains "Patient List"
    And the menu "clinical" contains "Change Password"
    And the menu "clinical" contains "Enable two-factor auth"
    And the menu "clinical" contains "Logout"
    When I click "SMITH Jane" on patientlisting
    Then location is "Demographics"
    And the sidebar contains a link to "Consents"
    And the sidebar contains a link to "Proms"
    And the sidebar contains a link in section "Main" to "Baseline PROMS"
    And the sidebar contains a link in section "Main" to "Clinical"
    And the sidebar contains a link in section "Main" to "Pathology"
    And the sidebar contains a link in section "Main" to "Treatment"
    And the sidebar contains a link in section "Main" to "Survival"
    And the sidebar contains a link in section "Main" to "Follow up PROMS - 6 months"
    And the sidebar contains a link in section "Main" to "Follow up PROMS - Year 1"
    And the sidebar contains a link in section "Main" to "Follow up PROMS - Year 2"
    And the sidebar contains a section named "Follow up PROMS - Years 3 - 10"
    When I click "Proms" in sidebar
    Then I should see survey name option "Baseline PROMS"
    And I should see survey name option "Follow up PROMS - Year 1"
    And I should see survey name option "Follow up PROMS - Year 2"
    And I should see survey name option "Follow up PROMS - Years 3 - 10"
    And I should see survey name option "Follow up PROMS - 6 months"
    And I should see communication type option "QRCode"
    And I should see communication type option "Email"
