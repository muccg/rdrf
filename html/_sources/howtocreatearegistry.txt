.. _howtocreatearegistry:
How To Create a Registry in Ten Minutes
=======================================


Modelling
---------
1. Do this first on pen and paper!
2. Gather requirements of the data fields ( :ref:`"DEs" <des>` ) required
3. For each data field required, decide its :ref:`datatype <datatype>`. If a field is logically a :ref:`range <permittedvaluegroup>`, 
   work out the allowed :ref:`permitted values <permittedvaluegroup>`. Depending on the :ref:`datatype <datatype>`, decide any validation rules 
   for a numeric or float data type (max and/or min), and for a string data type, 
   the maximum length or pattern. Decide if any Derived Data Elements (calculated data type) are required.
4. Split them into logical groups (:ref:`sections <registries>`). Decide whether a section might be multiple
5. Portion related sections into :ref:`forms <registries>`
6. If a questionnaire is required for the registry, nominate a single form as a questionnaire


Creation
--------
1. Login as an admin and :ref:`navigate <navigation>` to "Registries" via the "Settings" button
2. Create a :ref:`registry <registries>` object and give it a name and code 
3. Create any :ref:`permitted value groups <permittedvaluegroup>` required ( adding
  any :ref:`permitted values <permittedvalue>` to the range.
4. Create DEs (one per data field ) - OR note an existing DE that does the job (*IMPORTANT* deleting a DE
  may affect other registries which use this cde - in the current version there are no safeguards to prevent
  a used DE from being deleted. Proceed with caution!)
5. Create the section objects and enter the cde codes required into the elements field
  NB. This *MUST* be a comma-delimited list (E,g  "CDEName, CDEAge" - no quotes)
6. Create forms and link them to the registry
7. Add section codes to the sections field

That's it as far as registry definition goes. The RDRF database now contains the definition of the registry.
It is already usable by end users without any re-start - the defined forms are created entirely dynamically.

Registry Use
------------
* To begin using the registry, login as a curator and assign patients to the registry.
* Patients can be added by navigating to the "Patient List" from the "Menu" button. Forms are then accessed for each Patient by clicking on "Modules".

Demo Site
---------

* A demo site is up and running at: https://rdrf.ccgapps.com.au/demo/
* Logins Provided (username/password):
    * admin/admin (for definition of new registries)
    * curator/curator (for data entry)
    * clinical/clinical (for data entry on clinical forms)
    * genetic/genetic (for data entry on genetic forms)
* A Demo Contact Registry and Demo Clinical Registry for Myotonic Dystrophy are provided.


