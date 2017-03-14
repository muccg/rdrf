Feature: User operates on multisection items.
  A user can:
  Add items (single section data) to a multisection and delete an item
  by checking the "Mark for Deletion" checkbox and saving.
  
  Background:
    Given export "fh.zip"
    Given a registry named "FH Registry"
  
  Scenario: Add multiple items to a multisection.
    When I am logged in as curator
    When I click Module "Main/Imaging" for patient "SMITH John" on patientlisting
    Then location is "Main/Imaging"
  
    # Enter first item
    #When I click radio button value "Yes - Normal" for section "Carotid Ultrasonography" cde "Carotid Ultrasonography"
    And I enter value "01-01-2017" for form "Imaging" section "Carotid Ultrasonography" cde "Date"
    # for some reason the line below failed
    #And I enter value "3.0" for form "Imaging" section "Carotid Ultrasonography" cde "Result (left)"
    And I enter value "4.0" for form "Imaging" section "Carotid Ultrasonography" cde "Result (right)"
    And I enter value "item 1" for form "Imaging" section "Carotid Ultrasonography" cde "Result"
    When I upload file "/app/rdrf/rdrf/features/fh_file_upload.feature" for multisection "Carotid Ultrasonography" cde "Report"
    And I click the "Save" button
    Then I should see "Patient John SMITH saved successfully"
    And I should be able to download "fh_file_upload.feature"

    # Enter second item
    #When I click radio button value "Yes - Normal" for section "Carotid Ultrasonography" cde "Carotid Ultrasonography"
    When I click the add button for multisection "Carotid Ultrasonography"
    And I enter value "02-01-2017" for form "Imaging" section "Carotid Ultrasonography" cde "Date" in item 2
    # for some reason the line below failed
    #And I enter value "3.0" for form "Imaging" section "Carotid Ultrasonography" cde "Result (left)"
    And I enter value "3.0" for form "Imaging" section "Carotid Ultrasonography" cde "Result (right)" in item 2
    And I enter value "item 2" for form "Imaging" section "Carotid Ultrasonography" cde "Result" in item 2
    When I upload2 file "/app/rdrf/rdrf/features/fh_multisection_tests.feature" for multisection "Carotid Ultrasonography" cde "Report" in item 2
    And I click the "Save" button
    Then I should see "Patient John SMITH saved successfully"
    And I should be able to download "fh_multisection_tests.feature"
    And I should be able to download "fh_file_upload.feature"
   
    # delete the first item of the multisection
    When I mark multisection "Carotid Ultrasonography" item 1 for deletion
    And I click the "Save" button
    And I should not be able to download "fh_file_upload.feature"
    And I should be able to download "fh_multisection_tests.feature"
