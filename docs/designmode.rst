.. _designmode:

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

5. Admin navigates to >Rdrf/Registry Forms and for each desired form in the registry, clicks the green "Add registry form" button.
6. Admin Selects the registry just created from the drop down list
7. Admin enters a name into the name field ( this name will appear on the form, eg "Physical Info")
8. Admin enters a comma-separated list of form section codes ( E.g. "FHPhysicalSection,FHPersonalitySection,FHAmbulatorySection" ( Note: The codes  should be unique and have no spaces - no quotes! - prefixing with registry code is conventional but
   advised) If the form is intended to be a public questionnaire form , check the questionnaire checkbox.
9. Save the form definition
10. For each section referred to in the comma separated list, add a section object by navigating to >Rdrf/Sections:
11. Click the green "Add Section" button and enter the section code ( used in the form definition )
12. Enter a display name for the section ( this will appear on the form above the fields defined for the section.)
13 Enter the CDE codes of any fields required in the elements list ( as a comma-separated list.) E.g. "CDEName,CDEAge,CDEHeight"
   Note: The system will check whether any entered CDE codes exist when the section object is saved - if any CDE code
   cannot be found in the system, the section object will not be created.