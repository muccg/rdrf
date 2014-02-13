REST Interface
==============

Updating CDE Data
-----------------
Using curl:
Posting a file:

curl -i   -F value=@LPK.filvar.vcf   <rdrf url>/<regcode>/patients/<patientid>/<formname>/<sectioncode>/<cdecode>

NB. The CDE with code <cdecode> must have datatype 'file'

Updating a non-file value

curl -i -H "Accept: application/json"  -X POST -d <value>   <rdrf url>/<regcode>/patients/<patientid>/<formname>/<sectioncode>/<cdecode>

NB. This only works at the CDE level at the moment.

Retrieving Data
===============

Examples
--------

curl --request GET <rdrf url>/fh/patients/1/fh/fhBMI/CDEHeight

retrieves json of height ( only)

curl --request GET <rdrf url>/fh/patients/1/fh/fhBMI

retrieves json of fhBMI section dictionary( code ==> value mapping )

curl --request GET <rdrf url>/fh/patients/1/fh

retrieves json of fh form ( JSON dictionary of section dictionaries )

curl --request GET <rdrf url>/fh/patients/1

retrieves JSON of all forms in fh registry for patient 1.






