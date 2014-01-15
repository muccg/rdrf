.. _sections:

Sections
========
A section is a named group of :ref:`fields` that can be inserted into a :ref:`form <forms>`.

Sections consist of:

.. _sectioncode:

Code
----
A section must have a non-blank code ( no spaces ) which is just a text value. Section codes must be unique.
The code of a section is used to refer to it, when used in a :ref:`form <forms>`.

Example: "FHSECTION34" or "SEC001"

.. _sectiondisplayname:
Display Name
------------
A string which will be displayed on the form to mark the start of the section.

Example: "Physical Characteristics" , "Contact Information" 

.. _sectionelements:
Elements
--------
The :ref:`cde <cdes>` codes of any fields comprising that section.

This *must* be a comma-demlited list of :ref:`cde codes <cdecode>`.

Example: "CDEName, CDEAge" 

( This would mean that the section would consist of two
data input fields - one defined by the :ref:`Common Data Element <cdes>` with :ref:`code <cdecode>` "CDEName"
and one defined by the Common Data Element with code "CDEAge" )

NB. Spaces between codes is *not* significant.


Allow multiple
--------------

A boolean flag indicating whether  multiple entries of this section can added ( or removed ) on the form.

Example
^^^^^^^

A friends section might be defined with cdes for name and email address etc.
Marking the section as "allow multiple" would cause an "Add" and "Remove" button
to be added to the form so multiple friends could be added ( or deleted.)

Extra
-----
If allow multiple is checked, this causes extra ( blank) copies of the initial section to be displayed.
 
