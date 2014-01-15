.. _datatypestring:
String Datatype
===============

Definition
----------
A text value.

Examples
--------

* hello world ( a string containing a space)
* Mary ( a word)
* " "  ( blank no quotes)
* The string 123 
* ^^%%$^%$ff  ( non alphanumeric characters )

.. _datatyperange:
Range Datatype
==============

Definition
----------
A set of allowed values ( usually represented as drop down list)

Ranges in RDRF are specified by the datatype keyword "range" and then selecting the appropriate :ref:`Permitted Value Group <permittedvaluegroup>` This entails that permitted value groups be created first.

Examples
--------
* shoe size : big, medium, small
* colour:  red, blue , green


.. _datatypecalculated:
Calculated Datatype
===================

Definition
----------
A value which is computed *client-side* from other values on the form.

To created a calculated CDE enter "calculated" as the datatype and then fill in the calculation field of the CDE.

Examples
--------
A calculation( for BMI ) could be coded as::
   
   var height = parseFloat(context.CDEHeight);
   var mass = parseFloat(context.CDEMass); 
   context.result = mass / ( height * height );


The "context" here is an abstraction representing the *other* cdes on the containing form.
( Hence these other CDEs must be present in some section of same form as the form containing
the calculated field, else an error will result.)

 









