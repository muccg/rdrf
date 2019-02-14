import yaml
import sys
import os.path
import re
from rdrf.helpers.utils import de_camelcase
from tempfile import TemporaryDirectory
from django.core.management import BaseCommand
from django.core.management.base import CommandError
from django.core.management import call_command

sys.stdout = open(1, 'w', encoding='utf-8', closefd=False)
explanation = """
Usage:

This command extracts English strings used in RDRF pages, forms and CDEs and
creates a "Django message 'po' file.
The command has two modes:

A) CDE labels and values translation: Extract strings from a yaml file and pump out to standard output:

> django-admin create_translation_file --yaml_file=<yaml file path> [--system_po_file <app level po file> ]  > <output po file>

NB. --system_po_file is the path the "standard po file" created by running django makemessages. By passing it
in the script avoids creating duplicate message ids  which prevent compilation.

B) Embedded HTML for headers, information text and splash screen in the yaml file - IMPORTANT: This
does NOT pump to standard output but delegates to django's "makemessages" command which unfortunately
writes out the po file only to the locale directory - so the existing po file there will be overwritten.
Therefore when building a complete po file ready for translation ensure that any intermediate output is copied to
separate files and them merged.

> django-admin create_translation_file --yaml_file=<yaml file path> --extract_html_strings

"""


class Command(BaseCommand):
    help = 'Creates a translation po file for a given registry'

    def add_arguments(self, parser):
        parser.add_argument('--yaml_file',
                            action='store',
                            dest='yaml_file',
                            default=None,
                            help='Registry Yaml file name')

        parser.add_argument('--system_po_file',
                            action='store',
                            dest='system_po_file',
                            default=None,
                            help='System po file')
        parser.add_argument('--extract_html_strings', action='store_true',
                            help='extract message strings from embedded html in yaml file')

    def _usage(self):
        print(explanation)

    def handle(self, *args, **options):
        extract_html_strings = options.get("extract_html_strings", False)
        file_name = options.get("yaml_file", None)
        system_po_file = options.get("system_po_file", None)
        self.msgids = set([])
        self.number = re.compile(r"^\d+$")
        self.translation_no = 1

        if not file_name:
            self._usage()
            raise CommandError("Must provide yaml file")

        if system_po_file:
            # splurp in existing messages in the system file so we don't dupe
            # when we cat this file to it
            self._load_system_messages(system_po_file)

        if extract_html_strings:
            self._extract_html_strings(file_name)
        else:
            self._emit_strings_from_yaml(file_name)

    def _extract_html_strings(self, yaml_file):
        # This dumps the embedded html templates from the yaml into a temporary folder and
        # and then runs makemessages over it to extract the strings into the
        # into the "system" po file
        self._load_yaml_file(yaml_file)
        htmls = []

        # splash screen
        splash_screen_html = self.data["splash_screen"]
        htmls.append(splash_screen_html)

        # form headers
        for form_dict in self.data["forms"]:
            form_header_html = form_dict["header"]
            htmls.append(form_header_html)

        # consent sections
        for consent_section_dict in self.data["consent_sections"]:
            information_text_html = consent_section_dict["information_text"]
            htmls.append(information_text_html)

        with TemporaryDirectory() as tmp_dir:
            os.chdir(tmp_dir)
            with open("tmp.rdrfdummyext", "w", encoding="utf-8") as f:
                f.write("\n".join(htmls))
            # This extracts strings from matching files in the current directory and merges them with
            # the existing _system_ po files ( under locals .. LC_MESSAGES )
            call_command('makemessages', verbosity=99, extensions=['rdrfdummyext'])

    def _load_system_messages(self, system_po_file):
        message_pattern = re.compile('^msgid "(.*)"$')
        with open(system_po_file, encoding='utf-8') as spo:
            for line in spo.readlines():
                line = line.strip()
                m = message_pattern.match(line)
                if m:
                    msgid = m.groups(1)[0]
                    self.msgids.add(msgid)

    def _load_yaml_file(self, file_name):
        with open(file_name, encoding='utf-8') as f:
            try:
                self.data = yaml.load(f)
            except Exception as ex:
                print("could not load yaml file %s: %s" % (file_name,
                                                           ex))

                sys.exit(1)

    def _emit_strings_from_yaml(self, file_name):
        self._load_yaml_file(file_name)

        for (comment, msgid) in self._get_strings_for_translation():
            self._print(comment, msgid)

    def _emit_strings_from_registry(self, registry_model):
        pass

    def _print(self, comment, message_string):
        if not message_string:
            return

        # multiple blank lines
        if not message_string.strip():
            return

        if message_string in self.msgids:
            return
        else:
            self.msgids.add(message_string)

        if self.number.match(message_string):
            return

        if comment:
            print("# %s" % comment)

        if "\n" in message_string:
            # probably wrong but compiler fails
            # if there are multilined messages
            # message_string = message_string.replace('\n',' ')
            lines = message_string.split("\n")
            first_line = lines[0]
            lines = lines[1:]

            print('msgid "%s"' % first_line.replace('"', ""))
            for line in lines:
                print('"%s"' % line.replace('"', ""))
            print('msgstr "translation goes here"')
            return

        # again we need to escape somwhow
        if '"' in message_string:
            message_string = message_string.replace('"', "")

        print('msgid "%s"' % message_string)
        msgstr = "TRANSLATION %s" % self.translation_no
        self.translation_no += 1
        print('msgstr "%s"' % msgstr)
        print()

    def _get_strings_for_translation(self):
        yield from self._yield_registry_level_strings()
        yield from self._yield_form_strings()
        yield from self._yield_consent_strings()
        yield from self._yield_menu_items()
        yield from self._yield_permission_strings()
        yield from self._yield_misc_strings()

    def _yield_registry_level_strings(self):
        # registry name
        yield None, self.data["name"]
        # todo process splashscreen
        # splash_screen_html = self.data["splash_screen"]
        yield None, None

    def _yield_form_strings(self):
        if self.data is None:
            raise Exception("No data?")

        for form_dict in self.data["forms"]:
            name = form_dict["name"]
            name_with_spaces = de_camelcase(name)

            comment = None
            yield comment, name_with_spaces

            # the header is html ...
            # header_html = form_dict["header"]
            # todo extract strings from header
            yield None, None
            yield from self._yield_section_strings(form_dict)

    def _yield_section_strings(self, form_dict):

        for section_dict in form_dict["sections"]:
            comment = None
            display_name = section_dict["display_name"]
            yield comment, display_name
            yield from self._yield_cde_strings(section_dict)

    def _yield_cde_strings(self, section_dict):
        for cde_code in section_dict["elements"]:
            cde_dict = self._get_cde_dict(cde_code)
            if cde_dict is None:
                continue

            cde_label = cde_dict["name"]

            instruction_text = cde_dict["instructions"]

            comment = None

            yield comment, cde_label
            yield comment, instruction_text

            yield from self._yield_pvg_strings(cde_dict)

    def _get_cde_dict(self, cde_code):
        for cde_dict in self.data["cdes"]:
            if cde_dict["code"] == cde_code:
                return cde_dict

    def _yield_consent_strings(self):
        for consent_section_dict in self.data["consent_sections"]:
            yield None, consent_section_dict["section_label"]
            for question_dict in consent_section_dict["questions"]:
                yield None, question_dict["question_label"]
                yield None, question_dict["instructions"]

    def _yield_pvg_strings(self, cde_dict):
        # we need to emit display values of drop down lists
        pvg_code = cde_dict["pv_group"]
        if pvg_code:
            # range exists
            pvg_dict = self._get_pvg_dict(pvg_code)
            if pvg_dict is None:
                comment = "missing pvg"
                yield comment, "???"
                return
            for value_dict in pvg_dict["values"]:
                display_value = value_dict["desc"]

                comment = None
                yield comment, display_value

    def _get_pvg_dict(self, pvg_code):
        for pvg_dict in self.data["pvgs"]:
            if pvg_dict["code"] == pvg_code:
                return pvg_dict

    def _get_field(self, thing, field):
        if isinstance(thing, dict):
            return thing[field]
        else:
            # assume a model
            return getattr(thing, field)

    def _yield_menu_items(self):
        # consent
        registry_name = self.data["name"]

        msgid = "Consents (%s)s" % registry_name
        yield None, msgid

        # permission matrix
        msgid = "Permissions (%s)s" % registry_name
        yield None, msgid

    def _yield_misc_strings(self):
        # Couldn't  get these strings to extract for some reason
        yield None, "Next of kin country"
        yield None, "Next of kin state"
        yield None, "Permission Matrix for %(registry)s"
        yield None, "Welcome"

    def _yield_permission_strings(self):
        from django.contrib.auth.models import Permission

        # These aren't in the yaml but depend on the configured auth groups
        for column_heading in [
            "Permission",
            "Clinical Staff",
            "Genetic Staff",
            "Parents",
            "Patients",
                "Working Group Curators"]:
            yield None, column_heading

        for permission_object in Permission.objects.all():
            yield None, permission_object.name
