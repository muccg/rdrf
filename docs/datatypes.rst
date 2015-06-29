

Datatypes
=========

There are multiple data types, including:

String Datatype
---------------

Definition
^^^^^^^^^^
A text value.

The maximum length of the string can be indicated.

Optionally a regular expression *pattern* can be entered in the :ref:`pattern` field of the cde definition

Examples
^^^^^^^^

* hello world ( a string containing a space)
* Mary ( a word)
* " "  ( blank no quotes)
* The string 123 
* ^^%%$^%$ff  ( non alphanumeric characters )


Integer Dataype
---------------

A whole number. Integer DEs can have a max or min value entered.

Examples
^^^^^^^^

12, -1,0 etc.



Float Datatype
--------------

Definition
^^^^^^^^^^

Real/Decimal numbers

Examples
^^^^^^^^

* 3.1415
* 4.00
* -1.5
* 0.0



Alphanumeric Datatype
---------------------

Definition
^^^^^^^^^^

[A-Za-z0-9]* 

Examples
^^^^^^^^
* THX1138
* fred
* 234
* h4x0r


Boolean Datatype
----------------

Definition
^^^^^^^^^^
Truth values

Examples
^^^^^^^^

* True
* False




Range Datatype
--------------
For more sophisticated DEs, a DE can incorporate Permitted Value Groups (PVG). 

Definition
^^^^^^^^^^
A set of allowed values (usually represented as drop down list)

Ranges in RDRF are specified by the datatype keyword "range" and then selecting the appropriate :ref:`Permitted Value Group <permittedvaluegroup>` This entails that permitted value groups be created first.

Examples
^^^^^^^^
* shoe size : big, medium, small
* colour:  red, blue , green



Calculated (Derived Date Element)
---------------------------------

Definition
^^^^^^^^^^
A value which is computed *client-side* from other values on the form.

To created a calculated DE enter "calculated" as the datatype and then fill in the calculation field of the DE.

Examples
^^^^^^^^
A calculation (for BMI) could be coded as::
   
   var height = parseFloat(context.CDEHeight);
   var mass = parseFloat(context.CDEMass); 
   context.result = mass / ( height * height );


The "context" here is an abstraction representing the *other* cdes on the containing form.
(Hence these other DEs must be present in some section of same form as the form containing
the calculated field, else an error will result).


File Datatype
-------------

Definition
^^^^^^^^^^

A file DE presents a file chooser widget to the user, allowing upload (and download) of a file from the user's 
local file system. NB. Only the uploaded file name is displayed - not the content.

Examples
^^^^^^^^

A consent form field.


Date Datatype
-------------

Definition
^^^^^^^^^^

A day, month, year combination

Examples
^^^^^^^^

* 4th Jan 2008
* 8 Dec 2078


ComplexField Datatype
---------------------

Definition
^^^^^^^^^^

A DE used to aggregate other DEs horizontally on the page.

The intent is mainly stylistic

Example
^^^^^^^

*  ComplexField(CDEName,CDEAge)

NB. This feature is experimental
