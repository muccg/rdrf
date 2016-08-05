Feature: Sanity Test

  Background:
    Given export "dd_with_data.zip"
    Given a registry named "Demyelinating Diseases Registry"

  Scenario: Curator logs in
    When I am logged in as curator
