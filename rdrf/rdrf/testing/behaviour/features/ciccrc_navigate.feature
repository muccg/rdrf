Feature: Navigate CIC Clinical (ICHOMCRC).
  As a user of CIC Clinical
  I want to be able to navigate the site.

  Background:
    Given export "ciccrc.zip"
    Given a registry named "ICHOM Colorectal Cancer"

  Scenario: Login, add patient, and navigate to PROMS request page
    When I am logged in as curator
    Then location is "Patient List"
    Then I add patient name "WARD Pendleton" sex "Male" birthdate "19-07-1994"
    Then I click "Proms" in sidebar
    Then location is "Patient Reported Outcomes"

  Scenario: Curator login
    When I am logged in as curator
    Then location is "Patient List"
    When I click "SMITH John" on patientlisting
    Then I click "Proms" in sidebar
    Then location is "Patient Reported Outcomes"
