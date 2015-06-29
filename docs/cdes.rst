.. _des:

Data Elements (DES)
===========================

RDRF allows creation of resusable fields, which can be dropped into the definition of  :ref:`sections` of :ref:`forms`, simply by entering their code into the elements field of the section definition ( in a comma separated list).

A DE is created by an admin user :ref:`navigating <navigation>` to "Data Elements"  in "Settings"

A DE definition consists of:


Code
----

A CDE must have a *globally unique code* (e.g. CDEAge, CDEInsulinLevel) which must not contain a space.

A meaningful code prefixed with CDE or the Registry Code is recommended. 



Name
----

A non blank "name" must also be entered, which will be used as the label of the component when it appears
on the form.


Desc
----

Origin of the field if externally loaded.


:
Datatype
--------

Each cde must have a data type specified by a text descriptor. Currently this descriptor is specified as free text  although this may change.


The allowed datatypes are as follows (NB. These are the literal words to type into the datatype field, *except* for ComplexField) 


* :ref:`string <datatypestring>`
* :ref:`integer <datatypeinteger>`   
* :ref:`alphanumeric <datatypealphanumeric>`
* :ref:`boolean <datatypeboolean>`
* :ref:`float <datatypeboolean>`
* :ref:`range <datatyperange>`
* :ref:`calculated <datatypecalculated>`
* :ref:`file <datatypefile>`
* :ref:`date <datatypedate>`
* :ref:`ComplexField <datatypecomplexfield>`




Pv group
--------
*IF* a range, select the desired :ref:`permitted value group <permittedvaluegroup>` here.


Allow multple
-------------
*IF* a range, checking this box will allow multple selections to be chosen from the range.

Example
^^^^^^^

* Brands of cars owned
* Medications taken


Max length
----------
*IF* a string value, the maximum number of characters allowed.


Max value
---------
*IF* an integer or a float value, the maximum magnitude allowed.


Min value
---------
*IF* an integer or a float value, the minimum magnitude allowed.

.. _cdeisrequired:
Is required
-----------
A check box indicating whether this field is mandatory (any datatype)

.. _cdepattern:
Pattern
-------
*IF* a string value, a regular expression used to indicate admissible values
(note these are always case sensitive in the current version).


Widget name
-----------
The name of a custom widget to visually present the data, or an an alternative widget 
from the default. *IMPORTANT!* The custom widget must already be provided in the codebase otherwise an error
will occur. If this field is left blank ( the default ), the default widget for the specified datatype
will be used, which should be good enough in 99% per cent of cases.



Calculation
-----------

*IF* a calculated field, a fragment of javascript outlined in :ref:`calculated fields <calculatedfields>`.
Leave blank if not a calculated field.






