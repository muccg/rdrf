Feature: Landing Page
  As the owner of RDRF
  I want the landing page to have general information about RDRF
  In order to let the world know about RDRF
  
  Background:
    Given development fixtures
    Given a registry named "Sample Registry"

  Scenario: Landing main page
    When I go home
    Then I should see "Need a patient registry for your department, clinic or community?"
    And I should see "RDRF allows for rapid creation of patient registries."
