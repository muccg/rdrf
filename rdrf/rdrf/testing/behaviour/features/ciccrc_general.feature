Feature: General functionality of CIC Clinical (ICHOMCRC).
  As a user of CIC Clinical
  I should be able to see page elements.

  Background:
    Given export "ciccrc.zip"
    Given a registry named "ICHOM Colorectal Cancer"

  Scenario: Clinical staff logs in, creates a patient, and checks the page elements
    When I am logged in as clinical
    And I add patient name "ANATID Annie" sex "Female" birthdate "13-04-1996"
    And location is "Demographics"
    Then the sidebar contains a section named "Modules"
    And the sidebar contains a section named "Follow up PROMS"
    And the sidebar contains a link to "Consents"
    And the sidebar contains a link to "Proms"
    And the sidebar contains a link in section "Modules" to "Patient Information"
    And the sidebar contains a link in section "Modules" to "Baseline PROMS"
    And the sidebar contains a link in section "Modules" to "Baseline Clinical"
    And the sidebar contains a link in section "Modules" to "Pathology"
    And the sidebar contains a link in section "Modules" to "Baseline Treatment"
    And the sidebar contains a link in section "Modules" to "Follow up and Survival"
    And the sidebar contains a link in section "Modules" to "BCCA - Bi-national Colorectal Cancer Audit"
    Then I click "Proms" in sidebar
    And the sidebar contains a link to "Demographics"
    And I should see survey name option "Baseline PROMS"
    And I should see survey name option "FollowUp PROMS"
    And I should see communication type option "QRCode"
    And I should see communication type option "Email"
