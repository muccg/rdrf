Feature: User uploads files.
  A user can:
  CRUD operations on file cdes:
  Upload a file corresponding to a file CDE and be provided with a
  download link for that file (CR)
  Update an existing file cde with a new file (U)
  Delete an uploaded file. (D)
  
  NB. The uploaded files are arbritrary - I chose some feature files for convenience.
  
  Background:
    Given export "fh.zip"
    Given a registry named "FH Registry"
  
  Scenario: Upload a file.
    When I am logged in as curator
    When I click Module "Main/Genetic Data" for patient "SMITH John" on patientlisting
    Then location is "Main/Genetic Data"
   
    # File cde is on genetic form where this cde is mandatory
    When I click radio button value "Yes" for section "Genetic Analysis" cde "Has the patient had a DNA test?"
    And I click the "Save" button
    Then I should see "Patient John SMITH saved successfully"
    
    When I upload file "/app/README.rst" for multisection "Laboratory Data" cde "Laboratory Report" in item 1
    And I click the "Save" button
    Then I should see "Patient John SMITH saved successfully"
    Then I should be able to download "README.rst"
    

  Scenario: Update (replace) an existing file cde.
    When I am logged in as curator
    When I click Module "Main/Genetic Data" for patient "SMITH John" on patientlisting
    Then location is "Main/Genetic Data"
   
    # File cde is on genetic form where this cde is mandatory
    When I click radio button value "Yes" for section "Genetic Analysis" cde "Has the patient had a DNA test?"
    And I click the "Save" button
    Then I should see "Patient John SMITH saved successfully"
    
    When I upload file "/app/README.rst" for multisection "Laboratory Data" cde "Laboratory Report" in item 1
    And I click the "Save" button
    Then I should see "Patient John SMITH saved successfully"
    Then I should be able to download "README.rst"
    
    When I upload file "/app/develop.sh" for multisection "Laboratory Data" cde "Laboratory Report" in item 1
    And I click the "Save" button
    Then I should see "Patient John SMITH saved successfully"
    Then I should be able to download "develop.sh"
    

#  Scenario: Delete (check the 'clear' box and save) an existing file cde.
#    When I am logged in as curator
#    When I click Module "Main/Genetic Data" for patient "SMITH John" on patientlisting
#    Then location is "Main/Genetic Data"
#   
#    # File cde is on genetic form where this cde is mandatory
#    When I click radio button value "Yes" for section "Genetic Analysis" cde "Has the patient had a DNA test?"
#    And I click the "Save" button
#    Then I should see "Patient John SMITH saved successfully"
#    
#    When I upload file "/app/rdrf/rdrf/features/fh_file_upload.feature" for multisection "Laboratory Data" cde "Laboratory Report"
#    And I click the "Save" button
#    Then I should see "Patient John SMITH saved successfully"
#    Then I should be able to download "fh_file_upload.feature"
#    
#    When I check the clear checkbox for multisection "Laboratory Data" cde "Laboratory Report" file "fh_file_upload.feature"
#    And I click the "Save" button
#    Then I should see "Patient John SMITH saved successfully"
#    #And I should not be able to download "fh_file_upload.feature"
