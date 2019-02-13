from django.core.management.base import BaseCommand
from django.db import transaction
from rdrf.services.io.defs.importer import Importer


class Command(BaseCommand):
    help = 'Imports a given registry file'

    def add_arguments(self, parser):
        parser.add_argument('--file',
                            action='store',
                            dest='registry_file',
                            default=None,
                            help='Registry Import file name')

        parser.add_argument('--format',
                            action='store',
                            dest='import_format',
                            default='yaml',
                            choices=['yaml', 'json'],
                            help='Import format: yaml or json')

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
                raise NotImplementedError("%s not supported yet" % import_format)

            with transaction.atomic():
                importer.create_registry()
