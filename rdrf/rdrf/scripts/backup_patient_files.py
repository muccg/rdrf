import os
import django
django.setup()

from registry.patients.models import Patient, PatientConsent
from rdrf.models.definition.models import CDEFile
from rdrf.models.definition.models import ClinicalData
from rdrf.helpers.utils import forms_and_sections_containing_cde
from rdrf.forms.dynamic.registry_specific_fields import RegistrySpecificFieldsHandler
import shutil
from django.conf import settings
from rdrf.db.filestorage import get_id, get_file
from rdrf.models.definition.models import CommonDataElement


def backup_patient_consents(patient, isBackedup=False):
    consents = PatientConsent.objects.filter(patient=patient.id)
    for consent in consents:
        consent_file = settings.MEDIA_ROOT + "/" + str(consent.form)
        if os.path.isfile(consent_file):
            dir_name = "patient_id_" + str(patient.id) + "/consents"
            backup_patient_consents_dir = create_backup_dir(dir_name)
            print("PATIENT CONSENT file: %s" % consent_file)
            print("Backup directory %s" % backup_patient_consents_dir)
            copy_file(consent_file, backup_patient_consents_dir)
            isBackedup = True
    return isBackedup


def backup_cdefiles(patient, isBackedup=False):
    registry_model = patient.rdrf_registry.first()
    cds = ClinicalData.objects.all().filter(django_id=patient.id, django_model="Patient", registry_code=registry_model.code, collection='cdes')
    #data = patient.get_dynamic_data(registry_model)
    for cd in cds:
        data = cd.data
        if data is not None:
            cdefiles_generator = find_cdefiles(data)
            for form_dict, section_dict, cdefile_dict in cdefiles_generator:
                cdefile_value = cdefile_dict['value']
                cdefile_id = get_id(cdefile_value)
                if cdefile_id:
                    cdefile_item, cdefile_filename = get_file(cdefile_id)
                    cde_file = settings.MEDIA_ROOT + "/" + str(cdefile_item)
                    if os.path.isfile(cde_file):
                        dir_name = "patient_id_" + str(patient.id) + "/cdefiles" + "/" + registry_model.code + "/" + form_dict['name'] + "/context_id_" + str(data['context_id']) +  "/" + section_dict['code'] + "/" + cdefile_dict['code'] + "/cdefile_id_" + str(cdefile_id)
                        backup_cdefiles_dir = create_backup_dir(dir_name)
                        print("CDE file: %s" % cde_file)
                        print("Backup directory %s" % backup_cdefiles_dir)
                        copy_file(cde_file, backup_cdefiles_dir)
                        isBackedup = True
    return isBackedup


def backup_reg_specific(patient, isBackedup=False):
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
                    re_spec_cde_file = settings.MEDIA_ROOT + "/" + str(cdefile_item)
                    if os.path.isfile(re_spec_cde_file):
                        dir_name = "patient_id_" + str(patient.id) + "/cdefiles" + "/" + registry_model.code + "/reg_spec/" + reg_spec_cde_dict['code'] + "/cdefile_id_" + str(cdefile_id)
                        backup_reg_spec_file_dir = create_backup_dir(dir_name)
                        print("Registry specific file: %s" % re_spec_cde_file)
                        print("Backup directory %s" % backup_reg_spec_file_dir)
                        copy_file(re_spec_cde_file, backup_reg_spec_file_dir)
                        isBackedup = True
    return isBackedup


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


def create_backup_dir(dir_name):
    backup_dir_path = "/data/backup_files/" + dir_name
    if not os.path.exists(backup_dir_path):
        try:
            os.makedirs(backup_dir_path)
        except OSError as osex:
            print("Failed to create directory structure. Exception: %s " % osex)
    return backup_dir_path


def copy_file(src_file, dest_dir):
    try:
        shutil.copy2(src_file, dest_dir)
    except Exception as ex:
        print("Failed to copy file. Exception: %s " % ex)


if __name__ == "__main__":
    patients = Patient.objects.all()
    for patient in patients:
        print(" ************************* Patient ID:%s ************************** " % patient.id)
        print("......Backing up PATIENT CONSENT file......")
        is_backup = backup_patient_consents(patient)
        if is_backup is False:
            print("No data to perform backup")
        print("......Backing up ClinicalData CDEFile......")
        is_backup = backup_cdefiles(patient)
        if is_backup is False:
            print("No data to perform backup")
        print("......Backing up Registry Specific File......")
        is_backup = backup_reg_specific(patient)
        if is_backup is False:
            print("No data to perform backup")
        print(" ***************************************************************** ")
