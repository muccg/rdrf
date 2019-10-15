import time
import json
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

    display_users = False

    users_listing = []

    def add_arguments(self, parser):
        parser.add_argument('--man', action='store_true',
                            help='Help about this command.')
        parser.add_argument('--users', action='store_true',
                            help='List the patients who are crashing the site.')
        parser.add_argument('--references', action='store_true',
                            help='List obsolete ClinicalData (default)')
        parser.add_argument('--json', action='store_true',
                            help='Format result in JSON')

    @catch_and_log_exceptions
    def handle(self, *args, **options):
        start = time.time()

        print("Detecting form/section/cde codes that are in the ClinicalData data but does not exists anymore...\n")

        if options['man']:
            self.display_help()
            exit(0)

        self.display_users = options['users']

        bad_codes = self.get_bad_codes()

        if not self.display_users:
            self.display_bad_codes(bad_codes)

        if options['json']:
            print("")
            print(json.dumps(self.users_listing))

        end = time.time()
        print("")
        self.stdout.write(self.style.SUCCESS(f"Script ended in {end - start} seconds."))

    def display_bad_codes(self, bad_codes):
        if bad_codes:
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

    def get_bad_codes(self):
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

        # Users header
        if self.display_users:
            self.display_user_row("PATIENT ID", "CONTEXT ID", "TYPE", "NAME/CODE", "VALUE")
            self.display_user_row("----------", "---------", "---------", "-------------------------", "---------")

        # Retrieve bad codes from ClinicalData.
        clinicaldatas = ClinicalData.objects.all()
        for clinicaldata in clinicaldatas:
            if clinicaldata.collection == "history":
                bad_codes = self.get_bad_codes_from_collection(clinicaldata.data, form_names, section_codes, cde_codes, bad_codes)

        return bad_codes

    def get_bad_codes_from_collection(self, collection_cdes_data, form_names, section_codes, cde_codes, bad_codes):
        patient_id = collection_cdes_data['django_id']
        context_id = collection_cdes_data['context_id']
        for form in collection_cdes_data['record']['forms']:
            if form["name"] not in form_names and form["name"] not in bad_codes["form_names"]:
                if self.display_users:
                    self.users_listing.append(self.display_user_row(patient_id, context_id, "form", form["name"]))
                bad_codes["form_names"].append(form["name"])
            for section in form["sections"]:
                if section["code"] not in section_codes and section["code"] not in bad_codes["section_codes"]:
                    if self.display_users:
                        self.users_listing.append(self.display_user_row(patient_id, context_id, "section", section["code"]))
                    bad_codes["section_codes"].append(section["code"])
                if section["allow_multiple"]:
                    for sub_cdes in section["cdes"]:
                        for cde in sub_cdes:
                            if cde["code"] not in cde_codes and cde["code"] not in bad_codes["cde_codes"]:
                                if self.display_users:
                                    self.users_listing.append(self.display_user_row(patient_id, context_id, "cde", cde["code"], cde["value"]))
                                bad_codes["cde_codes"].append(cde["code"])
                else:
                    for cde in section["cdes"]:
                        if cde["code"] not in cde_codes and cde["code"] not in bad_codes["cde_codes"]:
                            if self.display_users:
                                self.users_listing.append(self.display_user_row(patient_id, context_id, "cde", cde["code"], cde["value"]))
                            bad_codes["cde_codes"].append(cde["code"])
        return bad_codes

    def display_user_row(self, patient_id, context_id, element, code, value='RDRF_NOT_SET_display_user_row'):
        formatted_patient_id = "{:<10}".format(patient_id)
        formatted_context_id = "{:<10}".format(context_id)
        formatted_element = "{:<9}".format(element)
        formatted_code = "{:<25}".format(code)

        if value != "RDRF_NOT_SET_display_user_row":
            self.stdout.write(self.style.ERROR(f"{formatted_patient_id} | {formatted_context_id} | {formatted_element} | {formatted_code} | {value}"))
            return {"patient_id": patient_id, "context_id": context_id, "type": element, "code": code, "value": value}
        else:
            self.stdout.write(self.style.ERROR(f"{formatted_patient_id} | {formatted_context_id} | {formatted_element} | {formatted_code} |"))
            return {"patient_id": patient_id, "context_id": context_id, "type": element, "code": code}
