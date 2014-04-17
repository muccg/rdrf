.. _workflows:

Workflows
=========

Overview
--------

There are two basic modes in which RDRF is intended to be used: Design mode ( for creating new registries )
and User Mode ( for adding/editing and viewing patient data in a registry that has been created.)

Only administrators can add new registries, forms, sections or common data elements.

Important Point: Once Common Data elements and sections  are created they can be used by more than one registry.
But altering a data element or section that is in use will immediately affect any registries which use it.

Additionally, a public interface is provided when a registry form is nominated to be a questionnaire.
See :ref:`questionnaires <questionnaires>`.


Roles
=====

Each workflow in RDRF is intended to be performed by a user with a distinct role.

Admin
-----
Can do anything
Create and modify registry definitions
Import and Export registries

Curators
--------
Manage membership of patients in working groups within a registry

Clinicians
----------
Enter and view data on patients in a working group within a registry.



Design Mode Workflow
--------------------

Modelling
---------
Coming soon

Creating a Registry
-------------------

Assuming all CDEs have already been created:

1. Admin logs in and navigates to  >Rdrf/Registries
2. Admin clicks on green "Add registry" button.
3. Admin fills in Name, code and description of registry ( code must be unique and not contain spaces)
4. Admin pastes a html splash screen into the Splash screen field ( this will be linked to on the main page)

5. Admin navigates to >Rdrf/Registry Forms and for each desired form in the registry, clicks the green "Add registry form"
   button.
6. Admin Selects the registry just created from the drop down list
7. Admin enters a name into the name field ( this name will appear on the form, eg "Physical Info")
8. Admin enters a comma-separated list of form section codes ( E.g. "FHPhysicalSection,FHPersonalitySection,FHAmbulatorySection"
   ( Note: The codes  should be unique and have no spaces - no quotes! - prefixing with registry code is conventional but
   advised) If the form is intended to be a public questionnaire form , check the questionnaire checkbox.
9. Save the form definition


10. For each section referred to in the comma separated list, add a section object by navigating to >Rdrf/Sections:
11. Click the green "Add Section" button and enter the section code ( used in the form definition )
12. Enter a display name for the section ( this will appear on the form above the fields defined for the section.)
13 Enter the CDE codes of any fields required in the elements list ( as a comma-separated list.) E.g. "CDEName,CDEAge,CDEHeight"
   Note: The system will check whether any entered CDE codes exist when the section object is saved - if any CDE code
   cannot be found in the system, the section object will not be created.


User Mode Workflows
===================

Adding a Patient to a Registry
------------------------------
Coming Soon

Entering ( and viewing existing ) Registry Data for a Patient
------------------------------------

1. Login as a clinician
2. Navigate to >Patients/Patients
3. Select the required registry ( if more than one appears ) in the Registry drop down and click Search
4. Click on the Show Forms button of the required patient
5. Launch the required Registry form from the pop up
6 Enter in any required data and click save




Approving a questionnaire response
----------------------------------

Coming Soon





