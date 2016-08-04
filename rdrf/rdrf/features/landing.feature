Feature: Landing Page
  As the owner of RDRF
  I want the landing page to have general information about RDRF
  In order to let the world know about RDRF
  
  Background:
    Given export "dd_with_data.zip"


  Scenario: Landing main page
    When I go to "/"
    Then I should see "Need a patient registry for your department, clinic or community?"
    And I should see "RDRF allows for rapid creation of patient registries."
