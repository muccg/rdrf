from rdrf.helpers.transform_cd_dict import structure_valid, transform_cd_dict
from rdrf.models.definition.models import ClinicalData
from django.db import transaction
"""
Custom Script
GitHub Repo: rdrf
Issue#1007(in rdrf-ccg repo)
Move CDEs from one section to another and migrate data on ClinicalData form
"""
import django
django.setup()


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
                if structure_valid(cde_codes, source_section_code, target_section_code, cd.data):
                    print(" Structure validated and now transforming clinicaldata dictionary......")
                    cd.data = transform_cd_dict(cde_codes, source_section_code, target_section_code, cd.data)
                    print("Saving ClinicalData....")
                    cd.save()
                print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    except Exception as ex:
        print("******* Rolling back......CDE migration FAILED with an exception: %s *******" % ex)


if __name__ == "__main__":
    print(" Calling migrate_cdes_clinicaldata ......")
    migrate_cdes_clinicaldata()
