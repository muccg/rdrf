.. _cdes:

Common Data Elements (CDES)
===========================

RDRF allows creation of resusable fields, which can be dropped into the definition of  :ref:`sections` of :ref:`forms`, simply by entering their code into the elements field of the section definition ( in a comma separated list.)

A CDE is created in the admin interface by :ref:`navigating <navigation>` to "Home >> Rdrf >> Common Data Elements"  in the :ref:`sidebar`.

A CDE definition consists of:

.. _cdecode:
Code
----

A CDE must have a *globally unique code* ( e.g. CDEAge, CDEInsulinLevel ) which must not contain a space.

A meaningful code prefixed with CDE is recommended. 


.. _cdename:
Name
----

A non blank "name" must also be entered , which will be used as the label of the component when it appears
on the form.

.. _cdedatatype:
Datatype
--------

Each cde must have a data type specified by a text descriptor. Currently this descriptor is specified as free text  although this may change.


The allowed datatypes are as follows ( NB. These are the literal words to type into the datatype field, *except* for ComplexField ) 

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






  
