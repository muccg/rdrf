"""
Custom Script
For Issue 1007 Move CDEs from one section to another and migrate data on ClinicalData form
"""
import sys
import django
django.setup()
#from django.db import transaction, IntegrityError, DatabaseError
from django.db import transaction
from rdrf.models.definition.models import ClinicalData
from rdrf.helpers.transform_cdes import tranform_data_dict

def migrate_cdes_clinicaldata():
    params = [["CDE00016", "FHCRP"], "SEC0005", "SEC0003"]

    # if history : cd[0]['record']['forms']
    # Collection are cdes, history, progress or registry_specific_patient_data
    # cds is ClinicalDataQuerySet
    # django_id is patient id
    #cds = ClinicalData.objects.filter(collection='cdes',registry_code="fh",django_model="Patient",django_id=13)
    cds = ClinicalData.objects.filter(collection='cdes', registry_code="fh", django_model="Patient")

    if len(cds) == 0:
        print("No Clinicaldata found")

    try:
        with transaction.atomic():
            # cd is object instance of ClinicalData model
            for cd in cds:
                # cd_dict is clinicalData Dictionary
                cd.data = tranform_data_dict(cd.data, *params)
                cd.save()
    except Exception as ex:
        cd.log("run failed - rolled back: %s" % ex)


if __name__ == "__main__":
    print("Calling migrate_cdes_clinicaldata from s")
    migrate_cdes_clinicaldata()
