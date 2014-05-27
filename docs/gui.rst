.. _gui:

RDRF Graphical User Interface
=============================

RDRF is a Django web application and accessed via any web browser ( E.g. Chrome or Firefox.)

The system uses the standard Django Admin interface to provide access to the application.

The admin interface consists of a single left sidebar which presents a tree structure.
Pages in the admin interface are referred to in this document using a notation like this:

.. _navigation:

Navigation Notation
===================

"Home >> Rdrf >> Sections" means the location you end up at if you "Mouse over" the Rdrf item in the :ref:`sidebar` under the :ref:`home` icon and then click "Sections"

.. _sidebar:

Sidebar
======

Note: Items marked "Under Review" are not finalised.

The left sidebar tree consists of:

.. _home:
Home
----
The root of the admin interface showing all objects that can be administered.

.. _auth:
Auth
----
Provides adminstration of user groups and group level permissions.

.. _configuration:
Configuration
-------------
Under review

.. _genetic:
Genetic
-------

Under review

.. _groups:
Groups
------
Administer users and working groups

.. _iprestrict:
Iprestrict
----------
Restrict access to the application based on IP

.. _patients:
Patients
--------
Add or edit patient information ( contact details.) 

.. _countries:
Countries
---------
Add or edit country information.

.. _doctors:
Doctors
-------
Add or edit doctors

.. _nextofkinrelationships:
Next of Kin Relationships
-------------------------
Add relationship name ( e.g. brother )

.. _parents:
Parents
-------
Under review

.. _patientregistrys:
Patient registrys
-----------------

Used to assign ( or remove ) a patient to a registry. Patients can be assigned to more than 
one registry. Removing a patient from a registry does not delete the patient, only the patient's
*membership* in *that* registry.

.. _patients:
Patients
--------
Allows editing of patient contact data.

.. _states:
States
------
Editing of states or territories in a country.

.. _rdrf:

Rdrf
----
The main admin interface for RDRF. Add or edit objects here to create new :ref:`registrys` and define the :ref:`forms`, :ref:`sections` and :ref:`Common Data Elements <cdes>` they use.

.. _savedqueries:

Savedqueries
------------
Under review

.. _sites:

Sites
-----
Under review

.. _userlog:

Userlog
-------
Under review






.. _conceptualstructure:

Conceptual Structure
====================


Registry Specification Interface
================================

The registry specification interface uses the standard Django Admin Interface to provide access to registry definitions at runtime. This is only accessible
by admins of the application, and is not intended to be used by normal end-users. It is here
that registry specifications ( definitions ) are created or imported.

The interface consists of a left sidebar 

The patient data entry interface is a standard Django admin interface to allow creation of patients and basic 
contact data. Patients created via this interface can be assigned to one or more registries.

The registry end-user interface is accessed via the registry :ref:`dashboard`. 
