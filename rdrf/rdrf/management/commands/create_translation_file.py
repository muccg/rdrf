from django.core.management.base import BaseCommand
import yaml
import sys
from rdrf.utils import decamelcase

class Command(BaseCommand):
    help = 'Creates a translation po file for a given registry'

    def add_arguments(self, parser):
        parser.add_argument('--yaml_file',
                            action='store',
                            dest='yaml_file',
                            default=None,
                            help='Registry Yaml file name')


    def handle(self, *args, **options):
        file_name = options.get("yaml_file")
        if file_name is None:
            raise Exception("--yaml_file argument required")

        with open(file_name) as f:
            try:
                data = yaml.load(f)
            except Exception as ex:
                print("could not load yaml file %s: %s" % (file_name,
                                                           ex))

                sys.exit(1)

            for comment, msgid in self._get_strings_for_translation(data):
                self._print(comment, msgid)

    def _print(self, comment, message_string):
        if comment:
            print("# %s" % comment)
        
        print('msgid "%s"' % message_string) 
        print('msgstr "translation goes here"')
        print(" ")

    def _get_strings_for_translation(self, data):
        self._yield_form_strings(data)


    def _yield_form_strings(self, data):
        
        for form_dict in data["forms"]:
            name = form_dict["name"]
            name_with_spaces = decamelcase(name)
            comment = None
            yield comment, name_with_spaces

            self._yield_section_strings(form_dict)

    def _yield_section_strings(self, form_dict):
        for section_dict in form_dict["sections"]:
            comment = None
            display_name = section_dict["display_name"]

            yield comment, display_name

            self._yield_cde_strings(section_dict)

    def _yield_cde_strings(self, section_dict):
        for cde_dict in section_dict["cdes"]:
            cde_label = cde_dict["name"]
            instruction_text = cde_dict["instructions"]

            comment = None

            yield comment, cde_label
            yield comment, instruction_text

            self._yield_pvg_strings(cde_dict)

    def _yield_pvg_strings(self, cde_dict):
        # we need to emit display values of drop down lists
        pvg_code = cde_dict["pv_group"]
        if pvg_code:
            # range exists
            pvg_dict = self._get_pvg_dict(pvg_code)
            for value_dict in pvg_dict["values"]:
                display_value = value_dict["description"]
                comment = None
                yield comment, display_value
                
            
            
            
            
            
            
            
