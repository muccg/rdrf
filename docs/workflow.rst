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


User Mode Workflows
===================

Adding a user ( curator or clinician, or genetic staff)
-------------------------------------

1. Admin logs in
2. Clicks on Users in left panel.
3. Clicks Add User button on right
4. Enters Username and password
5. Clicks Next
6. Enters personal information
7. Checks "Staff Status"
8. Control-Clicks Working Group Curators for curator ( or Clinical Staff for clinician, or Genetic Staff for
   genetic staff.)

9. Control-clicks the required working groups and registries ( if more than one.)
10. Clicks save.




Adding a Patient to a Registry
------------------------------
1. Curator or clinician logs in.
2. Clicks Quck Links /Patients
3. Click Add Patient ( or edit patient)
4. Control-click on each registry that is listed that you would like the patient to be  a member of.
   ( NB. If a clinician or curator has access to only one registry, it will already be assigned.)


Entering ( and viewing existing ) Demographic Data for a Patient
----------------------------------------------------------------

1. Login as a clinician
2. Click Patients in "Quick Links" panel.
3. Click Details button in Demographics column of patient list.
4. Edit contact details for the patient.
5 Click Save button

Changing Working Group for a Patient
------------------------------------
1. Login as curator
2. Click on patients in Quick Links Panel
3. Click on details button in demographics column.
4. Select required working group ( NB. workings group in the dropdown will only be those for which the curator has access.)



Entering / editing existing Clinical Data for a Patient
-------------------------------------------------------

1. Login in as a clinician
2. Click Patients in Quick Links panel.
3. If clinician has access to more than registry a drop down of registries is shown in the search area, otherwise no
   registry dropdown will appear and all operations will occur in the one registry.
4. Click the  "Show Modules" button in the patients list for the required patient - a pop up of available forms will
   appear ( except if there is only one defined clinical data form.)
5. Click the desired clinical data entry form.
6 The screen will show the required form.
7. Edit and click Save


Approving/Rejecting a Questionnaire response
----------------------------------

1. Curator or clinician logs in.
2. Click Questionnaire Responses in the Quick Links Panel
3. Click "Go" under "Process Questionnaire" to approve/reject a questionanaire
4. User reviews information in the submitted form and clicks approve ( or reject):
   If approve is clicked, a new patient will be created in the registry and working group indicated in the form.
   If reject is clicked, no patient record will be created


Adding a new working group
--------------------------

1. Admin logs in
2. Put mouse over Groups /Working Groups in left panel ( and click)
3. Click green "Add Working Group" button
4. Enter name and save.

Changing the Working Groups of a Curator
----------------------------------------

1. As an admin , click on Users link in left panel
2. Click on the username of the curator required.
3. Control-click ( command-click for Mac ) on each working group in the combo box required for that user ( a curator in 2 working groups will see patients in both groups)
4. Click the Save button

Assigning a curator ( or clinician ) to a registry
--------------------------------------------------

1. As an admin , login and then click on the Users link in the left panel
2. Click on the username of the user required.
3. Control-click ( command-click for Mac) on each registry the user is meant to have access to.\
4. Click the Save button.

Adding Genes
------------

1. Genetic staff logs in.
2. Clicks on Genetic / Genes in left panel
3. Clicks on Add Gene
4. Clicks Save

Adding Laboratory
-----------------
1. Genetic Staff logs in.
2. Clicks on Genetic / Laboratories in left panel
3. Adds details
4. Clicks Save.







