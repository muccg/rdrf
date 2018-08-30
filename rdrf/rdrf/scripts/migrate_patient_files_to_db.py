import os
import shutil
import django
django.setup()

from django.db import transaction
from registry.patients.models import Patient, PatientConsent
from rdrf.models.definition.models import CDEFile, DBFileStorage
from rdrf.models.definition.models import ClinicalData
from rdrf.helpers.utils import forms_and_sections_containing_cde
from rdrf.forms.dynamic.registry_specific_fields import RegistrySpecificFieldsHandler
from django.conf import settings
from rdrf.db.filestorage import get_id, get_file
from rdrf.models.definition.models import CommonDataElement
from django.core.files import File


def migrate_patient_consent_files(patient, isMigrated=False):
    consents = PatientConsent.objects.filter(patient=patient.id)
    for consent in consents:
        consent_file_path = settings.MEDIA_ROOT + "/" + str(consent.form)
        if os.path.isfile(consent_file_path):
            try:
                with transaction.atomic():
                    print("Consent file ID: %s" % consent.id)
                    print("Consent filefield(filesystem): %s" % consent.form)
                    store_file_database(consent_file_path, consent)
                    print("UPDATED: dbfilestorage ID(database): %s" % get_dbfilestorage_id(consent.form))
                    print("UPDATED: filefield(database): %s" % consent.form)
                    print("**** Successfully uploaded file  **** ")
                    isMigrated = True
            except Exception as ex:
                print("Failed file migration to database storage: %s" % ex)
        elif get_dbfilestorage_id(consent.form):
            print("File '%s' already migrated to database with ID:%s" % (consent.form, get_dbfilestorage_id(consent.form)))
    return isMigrated


def migrate_clinicaldata_cdefiles(patient, isMigrated=False):
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
                    cdefile = get_cdefile(cdefile_id)
                    cdefile_path = settings.MEDIA_ROOT + "/" + str(cdefile.item)
                    if os.path.isfile(cdefile_path):
                        try:
                            with transaction.atomic():
                                print("CDE file ID: %s" % cdefile.id)
                                print("CDE filefield(filesystem): %s" % cdefile.item)
                                store_file_database(cdefile_path, cdefile)
                                print("UPDATED: dbfilestorage ID(database): %s" % get_dbfilestorage_id(cdefile.item))
                                print("UPDATED: filefield(database): %s" % cdefile.item)
                                print("**** Successfully uploaded file  **** ")
                                isMigrated = True
                        except Exception as ex:
                            print("Failed file migration to database storage: %s" % ex)
                    elif get_dbfilestorage_id(cdefile.item):
                        print("File '%s' already migrated to database with ID:%s" % (cdefile.item, get_dbfilestorage_id(cdefile.item)))
    return isMigrated


def migrate_reg_specific_files(patient, isMigrated=False):
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
                    reg_spec_cdefile = get_cdefile(cdefile_id)
                    reg_spec_cdefile_path = settings.MEDIA_ROOT + "/" + str(reg_spec_cdefile.item)
                    if os.path.isfile(reg_spec_cdefile_path):
                        try:
                            with transaction.atomic():
                                print("CDE file ID: %s" % reg_spec_cdefile.id)
                                print("CDE filefield(filesystem): %s" % reg_spec_cdefile.item)
                                store_file_database(reg_spec_cdefile_path, reg_spec_cdefile)
                                print("UPDATED: dbfilestorage ID(database): %s" % get_dbfilestorage_id(reg_spec_cdefile.item))
                                print("UPDATED: filefield(database): %s" % reg_spec_cdefile.item)
                                print("**** Successfully uploaded file  **** ")
                                isMigrated = True
                        except Exception as ex:
                            print("Failed file migration to database storage: %s" % ex)
                    elif get_dbfilestorage_id(reg_spec_cdefile.item):
                        print("File '%s' already migrated to database with ID:%s" % (reg_spec_cdefile.item, get_dbfilestorage_id(reg_spec_cdefile.item)))

    return isMigrated


def get_dbfilestorage_id(filename):
    try:
        dbfile = DBFileStorage.objects.get(filename=str(filename))
        return dbfile.id
    except DBFileStorage.DoesNotExist:
        return None


def store_file_database(file_path, file_field):
    try:
        file_obj = File(open(file_path, 'rb'))
        file_obj.name = os.path.basename(file_path)
        print("Uploading file '%s' to database...." % file_obj.name)
        if 'form' in dir(file_field):
            file_field.form = file_obj
        elif 'item' in dir(file_field):
            file_field.item = file_obj
        file_field.save()
        file_obj.close()
    except IOError as ioex:
        print("Failed uploading file to database: %s" % ioex)


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


def get_cdefile(file_id):
    try:
        cde_file = CDEFile.objects.get(id=file_id)
        return cde_file
    except CDEFile.DoesNotExist:
        return None, None


if __name__ == "__main__":
    patients = Patient.objects.all()
    for patient in patients:
        print(" ************************* Patient ID:%s ************************** " % patient.id)
        print("......Migrating PATIENT CONSENT file......")
        is_migrated = migrate_patient_consent_files(patient)
        if is_migrated is False:
            print("No data to perform migration")
        print("......Migrating ClinicalData CDEFile......")
        is_migrated = migrate_clinicaldata_cdefiles(patient)
        if is_migrated is False:
            print("No data to perform migration")
        print("......Migrating Registry Specific File......")
        is_migrated = migrate_reg_specific_files(patient)
        if is_migrated is False:
            print("No data to perform migration")
        print(" ***************************************************************** ")
