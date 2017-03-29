from django.core.management.base import BaseCommand
import yaml
import sys
import re
from rdrf.utils import de_camelcase
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


    def _usage(self):
        print("django-admin create_translation_file registry_code=fh")
        print("OR")
        print("django-admin create_translation_file yaml_file=/data/fh.yaml")


    def handle(self, *args, **options):
        file_name = options.get("yaml_file", None)
        registry_code = options.get("registry_code", None)
        self.msgids = set([])
        self.current_path = None
        
        self.number = re.compile("^\d+$")
        
        if file_name is not None and registry_code is not None:
            self._usage()
            sys.exit(1)
            
        if registry_code:
            registry_model = Registry.objects.get(code=registry_code)
            self._emit_strings_from_registry(registry_model)
        else:
            self._emit_strings_from_yaml(file_name)

        print("# Total of %s message strings" % len(self.msgids))
        

    def _add_path(self, name):
        if self.current_path is None:
            self.current_path = name
        else:
            self.current_path = "%s/%s" % (self.current_path,
                                           name)

    def _clear_path(self):
        self.current_path = None
        

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

        if message_string in self.msgids:
            return
        else:
            self.msgids.add(message_string)
            

        if self.number.match(message_string):
            return
        if comment:
            print("# %s" % comment)
        print('msgid "%s"' % message_string) 
        print('msgstr "translation goes here"')
        print()

    def _get_strings_for_translation(self):
        yield from self._yield_form_strings()

    def _yield_form_strings(self):
        if self.data is None:
            raise Exception("No data?")
        
        for form_dict in self.data["forms"]:
            name = form_dict["name"]
            name_with_spaces = de_camelcase(name)
            
            comment = self.current_path
            yield comment, name_with_spaces

            yield from self._yield_section_strings(form_dict)
            self._clear_path()
            

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

            comment = self.current_path

            yield comment, cde_label
            yield comment, instruction_text

            yield from self._yield_pvg_strings(cde_dict)

    def _get_cde_dict(self, cde_code):
        for cde_dict in self.data["cdes"]:
            if cde_dict["code"] == cde_code:
                return cde_dict
        

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
        
                
            
            
            
            
            
            
            
