Feature: User uploads files.
  A user can:
  Upload a file corresponding to a file CDE and be provided with a
  download link for that file.
  Delete an uploaded file.
  
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
    
    When I upload file "/app/rdrf/rdrf/features/fh_file_upload.feature" for multisection "Laboratory Data" cde "Laboratory Report"
    And I click the "Save" button
    Then I should see "Patient John SMITH saved successfully"
    #Then I should see "Currently:"
    Then I should be able to download "fh_file_upload.feature"
    
    
     
