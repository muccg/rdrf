from django.core.management.base import BaseCommand
import yaml
import sys
import re
from rdrf.utils import de_camelcase
from rdrf.utils import process_embedded_html
from rdrf.models import Registry


class Command(BaseCommand):
    help = 'Creates a translation po file for a given registry'

    def add_arguments(self, parser):
        parser.add_argument('--yaml_file',
                            action='store',
                            dest='yaml_file',
                            default=None,
                            help='Registry Yaml file name')
        parser.add_argument('--registry_code',
                            action='store',
                            dest='registry_code',
                            default=None,
                            help='Registry Code')

        parser.add_argument('--system_po_file',
                            action='store',
                            dest='system_po_file',
                            default=None,
                            help='System po file')



    def _usage(self):
        print("django-admin create_translation_file registry_code=fh")
        print("OR")
        print("django-admin create_translation_file yaml_file=/data/fh.yaml")


    def handle(self, *args, **options):
        self.testing = True
        
        file_name = options.get("yaml_file", None)
        registry_code = options.get("registry_code", None)
        system_po_file = options.get("system_po_file", None)
        self.msgids = set([])
        self.number = re.compile("^\d+$")
        
        if file_name is not None and registry_code is not None:
            self._usage()
            sys.exit(1)

        if system_po_file:
            # splurp in existing messages in the system file so we don't dupe
            # when we cat this file to it
            self._load_system_messages(system_po_file)
        
        if registry_code:
            registry_model = Registry.objects.get(code=registry_code)
            self._emit_strings_from_registry(registry_model)
        else:
            self._emit_strings_from_yaml(file_name)

        print("# Total of %s message strings" % len(self.msgids))

    def _load_system_messages(self, system_po_file):
        message_pattern = re.compile('^msgid "(.*)"$')
        with open(system_po_file) as spo:
            for line in spo.readlines():
                line = line.strip()
                m = message_pattern.match(line)
                if m:
                    msgid = m.groups(1)[0]
                    self.msgids.add(msgid)

    def _emit_strings_from_yaml(self, file_name):
        with open(file_name) as f:
            try:
                self.data = yaml.load(f)
            except Exception as ex:
                print("could not load yaml file %s: %s" % (file_name,
                                                           ex))

                sys.exit(1)

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
            #message_string = message_string.replace('\n',' ')
            lines = message_string.split("\n")
            first_line = lines[0]
            lines = lines[1:]
            
            print('msgid "%s"' % first_line.replace('"',""))
            for line in lines:
                print('"%s"' % line.replace('"', ""))
            print('msgstr "translation goes here"')
            return

        # again we need to escape somwhow
        if '"' in message_string:
            message_string = message_string.replace('"',"")

        print('msgid "%s"' % message_string) 
        if self.testing:
            # reverse string
            msgstr = message_string[::-1]
        else:
            msgstr = "Translation goes here"
            
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
        splash_screen_html = self.data["splash_screen"]
        comment = "From splash screen"
        for text in process_embedded_html(splash_screen_html, translate=False):
            yield comment, text
            
            

    def _yield_form_strings(self):
        if self.data is None:
            raise Exception("No data?")
        
        for form_dict in self.data["forms"]:
            name = form_dict["name"]
            name_with_spaces = de_camelcase(name)
            
            comment = None
            yield comment, name_with_spaces

            # the header is html ...
            header = form_dict["header"]
            yield "Preserve the HTML tags please!", header
            

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
            information_text = consent_section_dict["information_text"]
            yield from self._yield_text_from_html(information_text)
            
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
        if type(thing) is dict:
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

    def _yield_permission_strings(self):
        from django.contrib.auth.models import Permission

        # These aren't in the yaml but depend on the configured auth groups
        for column_heading in ["Permission", "Clinical Staff", "Genetic Staff","Parents","Patients","Working Group Curators"]:
            yield None, column_heading


        for permission_object in Permission.objects.all():
            yield None, permission_object.name

    def _yield_text_from_html(self, html):
        for text in process_embedded_html(html, translate=False):
            if text:
                yield None, text
            

