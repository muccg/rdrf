Feature: Sanity test history widget.
  Enter clinical data over time.
  Use the history widget to observe past values in tabular form.
  
  Background:
    Given export "fh.zip"
    Given a registry named "FH Registry"
  
  Scenario: Enter successive values for a field
    When I am logged in as curator
    When I click Module "Main/Medications" for patient "SMITH John" on patientlisting
    Then location is "Main/Medications"
    

    # NB. the quirk of the step - it's appending the input to whats there, not over typing into the field..

    When I enter value "foo" for form "Medications" section "Hypertensive Medication" cde "If other, enter medication name(s)"
    And I click the "Save" button
    Then the form value of section "Hypertensive Medication" cde "If other, enter medication name(s)" should be "foo"
     
    When I enter value "bar" for form "Medications" section "Hypertensive Medication" cde "If other, enter medication name(s)"
    And I click the "Save" button
    Then the form value of section "Hypertensive Medication" cde "If other, enter medication name(s)" should be "foobar"
    
    When I enter value "baz" for form "Medications" section "Hypertensive Medication" cde "If other, enter medication name(s)"
    And I click the "Save" button
    Then the form value of section "Hypertensive Medication" cde "If other, enter medication name(s)" should be "foobarbaz"
    And History for form "Medications" section "Hypertensive Medication" cde "If other, enter medication name(s)" shows "foo,foobar,foobarbaz"

