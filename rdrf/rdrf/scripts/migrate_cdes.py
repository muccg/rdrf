"""
Custom Script
GitHub Repo: rdrf 
Issue#1007(in rdrf-ccg repo) 
Move CDEs from one section to another and migrate data on ClinicalData form
"""
import sys
import django
django.setup()
from django.db import transaction
from rdrf.models.definition.models import ClinicalData
from rdrf.helpers.transform_cdes import transform_data_dict, InvalidDictionaryStructureException


def migrate_cdes_clinicaldata():
    cde_codes = ["CDE00016", "FHCRP"]
    source_section_code = "SEC0005"
    target_section_code = "SEC0003"

    # Collection are cdes, history, progress or registry_specific_patient_data
    # cds is ClinicalDataQuerySet and django_id is patient id
    cds = ClinicalData.objects.filter(collection='cdes', registry_code="fh", django_model="Patient")

    if len(cds) == 0:
        print("No Clinicaldata found")

    try:
        with transaction.atomic():
            # cd is object instance of ClinicalData model
            for cd in cds:
                print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
                print("******* Patient id=%s *******" % cd.django_id)
                print(" Calling transform_data_dict ......")
                new_cd_data = transform_data_dict(cde_codes, source_section_code, target_section_code, cd.data)
                if(new_cd_data):
                    print("Saving ClinicalData....")
                    cd.data = new_cd_data
                    cd.save()
                print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@") 
    except Exception as ex:
        print("******* Rolling back......CDE migration FAILED with an exception: %s *******" % ex)


if __name__ == "__main__":
    print(" Calling migrate_cdes_clinicaldata ......")
    migrate_cdes_clinicaldata()
