import os
import shutil
import django
django.setup()

from django.db import transaction
from registry.patients.models import Patient, PatientConsent
from rdrf.models.definition.models import CDEFile
from rdrf.models.definition.models import ClinicalData
from rdrf.helpers.utils import forms_and_sections_containing_cde
from rdrf.forms.dynamic.registry_specific_fields import RegistrySpecificFieldsHandler
from django.conf import settings
from rdrf.db.filestorage import get_id, get_file
from rdrf.models.definition.models import CommonDataElement
from django.core.files import File


def migrate_patient_consents(patient, isMigrated=False):
    consents = PatientConsent.objects.filter(patient=patient.id)
    for consent in consents:
        consent_filefield = consent.form
        consent_file_path = settings.MEDIA_ROOT + "/" + str(consent.form)
        if os.path.isfile(consent_file_path):
            try:
                with transaction.atomic():
                    print("PATIENT CONSENT file: %s" % consent_filefield)
                    cfile = File(open(consent_file_path, 'rb'))
                    print(cfile.name)
                    # cfile.name = consent.filename   # change it to basename
                    # print(cfile.name)
                    print(os.path.basename(consent_file_path))
                    print(cfile.size)
                    consent.form = cfile
                    print(consent)
                    print(consent.form)
                    print("storing file to database....")
                    print(vars(consent))
                    print(vars(consent.form))
                    # consent.save()
                    print("saving consent....")
                    cfile.close()
                    print("closing file....")
                    isMigrated = True
            except Exception as ex:
                print("File migration to database failed %s" % ex)
    return isMigrated


def migrate_cdefile(patient, isMigrated=False):
    registry_model = patient.rdrf_registry.first()
    cds = ClinicalData.objects.all().filter(django_id=patient.id, django_model="Patient", registry_code=registry_model.code, collection='cdes')
    for cd in cds:
        data = cd.data
        if data is not None:
            cdefiles_generator = find_cdefiles(data)
            for form_dict, section_dict, cdefile_dict in cdefiles_generator:
                cdefile_value = cdefile_dict['value']
                cdefile_id = get_id(cdefile_value)
                if cdefile_id:
                    cdefile_item, cdefile_filename = get_file(cdefile_id)
                    cde_file_path = settings.MEDIA_ROOT + "/" + str(cdefile_item)
                    if os.path.isfile(cde_file_path):
                        try:
                            with transaction.atomic():
                                print("CDE file: %s" % cde_file_path)
                                cfile = File(open(cde_file_path, 'rb'))
                                # cfile.name = os.path.basename(cde_file_path)
                                print(cfile.name)
                                print(cfile.size)
                                isMigrated = True
                                # print("**** Successfully migrated patient consents file to database for patient %s ****" % consent.patient)            
                        except Exception as ex:
                            print("File migration to database failed %s" % ex)
    return isMigrated


def find_cdefiles(data):
    if "forms" in data:
        for form_dict in data["forms"]:
            for section_dict in form_dict['sections']:
                for cde_dict in section_dict["cdes"]:
                    if type(cde_dict) is list:
                        for item in cde_dict:
                            if is_file(item):
                                yield form_dict, section_dict, item
                    else:
                        if is_file(cde_dict):
                            yield form_dict, section_dict, cde_dict


def is_file(cde_dict):
    try:
        cde_model = CommonDataElement.objects.get(code=cde_dict['code'])
        if cde_model and cde_model.datatype == 'file':
            return True
        else:
            return False
    except CommonDataElement.DoesNotExist:
        return False


def migrate_reg_specific(patient, isMigrated=False):
    registry_model = patient.rdrf_registry.first()
    cds = ClinicalData.objects.all().filter(django_id=patient.id, django_model="Patient", registry_code=registry_model.code, collection='registry_specific_patient_data')
    for cd in cds:
        registry_data = cd.data
        for key, value in registry_data.items():
            reg_spec_cde_dict = {}
            reg_spec_cde_dict['code'] = key
            reg_spec_cde_dict['value'] = value
            if is_file(reg_spec_cde_dict):
                cdefile_id = get_id(reg_spec_cde_dict['value'])
                if cdefile_id:
                    cdefile_item, cdefile_filename = get_file(cdefile_id)
                    re_spec_cde_file_path = settings.MEDIA_ROOT + "/" + str(cdefile_item)
                    if os.path.isfile(re_spec_cde_file_path):
                        try:
                            with transaction.atomic():
                                print("Registry specific file: %s" % re_spec_cde_file_path)
                                isMigrated = True
                        except Exception as ex:
                            print("File migration to database failed %s" % ex)
    return isMigrated


if __name__ == "__main__":
    patients = Patient.objects.all()
    for patient in patients:
        print(" ************************* Patient ID:%s ************************** " % patient.id)
        print("......Migrating PATIENT CONSENT file......")
        is_migrated = migrate_patient_consents(patient)
        if is_migrated is False:
            print("No data to perform migration")
        # print("......Migrating ClinicalData CDEFile......")
        # is_migrated = migrate_cdefile(patient)
        # if is_migrated is False:
        #     print("No data to perform migration")
        # print("......Migrating Registry Specific File......")
        # is_migrated = migrate_reg_specific(patient)
        # if is_migrated is False:
        #     print("No data to perform migration")
        print(" ***************************************************************** ")
