from optparse import make_option
from django.core.management.base import BaseCommand
from django.db import transaction
from rdrf.importer import Importer


class Command(BaseCommand):
    help = 'Imports a given registry file'

    option_list = BaseCommand.option_list[1:] + (
        make_option('--file',
                    action='store',
                    dest='registry_file',
                    type="string",
                    default=None,
                    help='Registry Import file name'),

        make_option('--format',
                    action='store',
                    dest='import_format',
                    default='yaml',
                    type='choice',
                    choices=['yaml', 'json'],
                    help='Import format: yaml or json'),
    )

    def handle(self, *args, **options):
        file_name = options.get("registry_file")
        if file_name is None:
            raise Exception("--file argument required")
        import_format = options.get("import_format")
        with open(file_name) as import_file:
            registry_import_data = import_file.read()
            importer = Importer()
            if import_format == 'yaml':
                importer.load_yaml_from_string(registry_import_data)
            else:
                raise NotImplemented("%s not supported yet" % import_format)

            with transaction.commit_on_success():
                importer.create_registry()
