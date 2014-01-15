.. _howtocreatearegistry:
How To Create a Registry in Ten Minutes
=======================================

Modelling
---------

Do this first on pen and paper! 


* Gather requirements of the data fields ( :ref:`"CDEs" <cdes>` ) required
  - For each data field required , decide its :ref:`datatype <cdedatatype>`
  - If a field is logically a :ref:`range <permittedvaluegroup>` , work out the allowed :ref:`values <permittedvalue>`.
  - Depending on the :ref:`datatype <cdedatatype>`, decide any validation rules for a
    numeric ( :ref:`integer <datatypeinteger>` or :ref:`float <datatypefloat>` ) field max and/or min, for a :ref:`string <datatypestring>` field, the maximum length or pattern. 
    Decide if any :ref:`calculated fields <datatypecalculated>` are required.

* Split them into logical groups ( :ref:`sections` ). Decide whether a section might be multiple.

* Portion related sections into :ref:`forms`
  - If a questionnaire is required for the registry, nominate a single form as a questionnaire.


Creation
--------

* Login as an admin and :ref:`navigate <navigation>` to "Home >> Rdrf"
* Create a :ref:`registry <registries>` object and give it a name and code 
* Create any :ref:`permitted value groups <permittedvaluegroup>` required ( adding
  any :ref:`permitted values <permittedvalue>` to the range.
* Create cdes ( one per data field ) - OR note an existing CDE that does the job ( *IMPORTANT* deleting a cde
  may affect other registries which use this cde - in the current version there are no safeguards to prevent
  a used CDE from being deleted. Proceed with caution! )
* Create the section objects and enter the cde codes required into the elements field
  NB. This *MUST* be a comma-delimited list ( E,g  "CDEName, CDEAge" - no quotes )
  
* Create forms and link them to the registry
  Add section codes to the sections field

That's it as far as registry definition goes. The RDRF database now contains the definition of the registry.
It is already usable by end users without any re-start - the defined forms are created entirely dynamically
when loaded from the :ref:`dashboard`.

Registry Use
------------
* To begin using the registry, login as a curator and assign patients to the registry.
* Then from the :ref:`dashboard`, load the form required and update data.

Patients can be assigned to a registry by using the :ref:`patient registry admin object <patientregistrys>`.

