.. _permittedvaluegroup:

Permissible Values and Permitted Value Groups
===========================================

Permissible Values
------------------

A permissible value (PV) is just a single allowed value that comprises part of a value range.

Examples
--------

If the associated value range was intended to be a size range then examples might be

* small
* medium
* large

In the GUI, individual permissible values will appear as selectable options in a drop down list.



Permitted Value Group
---------------------
A permitted value group (PVG) is a set of permissible values. A PVG must be defined first, with PVs then defined and assigned to a PVG.
PVGS are defined by navigating to "Permissible Value Groups" under "Settings".

Click "Add" to create a new PVG.

A value group has a code which must be a unique non blank string value.

Once a permitted value group has been created, add permissible values to it.

Examples
--------
The decoupling of permitted value groups from cdes that make use of them allows different attributes 

(e.g. shoe size , hat size) to share the same value ranges (E.g. small, medium, large) as is done
in NINDS http://www.commondataelements.ninds.nih.gov )



