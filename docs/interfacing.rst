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

