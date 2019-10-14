import time
from datetime import datetime
from django.core.management.base import BaseCommand
from rdrf.helpers.utils import catch_and_log_exceptions
from rdrf.models.definition.models import ClinicalData, RegistryForm, CommonDataElement, Section

# do not display debug information for the node js call.
import logging
logger = logging.getLogger(__name__)


class ScriptUser:
    username = 'Doctor script'


class Command(BaseCommand):
    help = 'Doctor checkes the database or code health.'

    def add_arguments(self, parser):
        parser.add_argument('--man', action='store_true',
                            help='Help about this command')

    @catch_and_log_exceptions
    def handle(self, *args, **options):
        start = time.time()
        modified_patients = []

        if options['man']:
            self.display_help()
            exit(1)

        bad_codes = get_bad_codes()

        self.display_bad_codes(bad_codes)

        end = time.time()
        self.stdout.write(self.style.SUCCESS(f"Script ended in {end - start} seconds."))

    def display_bad_codes(self, bad_codes):
        if bad_codes:
            self.stdout.write(self.style.ERROR(f"You must clean these obsolete ClinicalData: "))
            self.stdout.write(self.style.ERROR(f""))
            if bad_codes['form_names']:
                self.stdout.write(self.style.ERROR(f"Forms"))
                self.stdout.write(self.style.ERROR(f"{bad_codes['form_names']}"))
                self.stdout.write(self.style.ERROR(f""))
            if bad_codes['section_codes']:
                self.stdout.write(self.style.ERROR(f"Section"))
                self.stdout.write(self.style.ERROR(f"{bad_codes['section_codes']}"))
                self.stdout.write(self.style.ERROR(f""))
            if bad_codes['cde_codes']:
                self.stdout.write(self.style.ERROR(f"CDEs"))
                self.stdout.write(self.style.ERROR(f"{bad_codes['cde_codes']}"))
                self.stdout.write(self.style.ERROR(f""))

    def display_help(self):
        print("-----------------------------\n")
        print("WHAT DOES IT DO?\n")
        print("-----------------------------\n")
        print("This admin command displays the form names, section codes and cde codes that are causing RDRF to crash.\n")
        print("\n-----------------------------\n")
        print("WHY DOES THE PROBLEM OCCUR?\n")
        print("-----------------------------\n")
        print("This situation happens when designers edit form names and section/cde codes. Our code logic does not erase or update the ClinicalData under these names and codes, causing the site to crash.\n")
        print("\n-----------------------------\n")
        print("WHAT SHOULD YOU DO?\n")
        print("-----------------------------\n")
        print("Till we update the edit code logic, you must create a script updating or removing these obsolete ClinicalData data.\n")


def get_bad_codes():
    bad_codes = {"form_names": [], "section_codes": [], "cde_codes": []}

    # Retrieve all existing form names.
    forms = RegistryForm.objects.all()
    form_names = []
    for form in forms:
        form_names.append(form.name)

    # Retrieve all cde_codes.
    cdes = CommonDataElement.objects.all()
    cde_codes = []
    for cde in cdes:
        cde_codes.append(cde.code)

    # Retrieve all section codes.
    sections = Section.objects.all()
    section_codes = []
    for section in sections:
        section_codes.append(section.code)

    # Retrieve bad codes from ClinicalData.
    clinicaldatas = ClinicalData.objects.all()
    for clinicaldata in clinicaldatas:
        if clinicaldata.collection == "cdes":
            bad_codes = get_bad_codes_from_collection(clinicaldata.data, form_names, section_codes, cde_codes, bad_codes)

    return bad_codes


def get_bad_codes_from_collection(collection_cdes_data, form_names, section_codes, cde_codes, bad_codes):
    for form in collection_cdes_data['forms']:
        if form["name"] not in form_names and form["name"] not in bad_codes["form_names"]:
            bad_codes["form_names"].append(form["name"])
        for section in form["sections"]:
            if section["code"] not in section_codes and section["code"] not in bad_codes["section_codes"]:
                bad_codes["section_codes"].append(section["code"])
            for cde in section["cdes"]:
                if cde["code"] not in cde_codes and cde["code"] not in bad_codes["cde_codes"]:
                    bad_codes["cde_codes"].append(cde["code"])
    return bad_codes
