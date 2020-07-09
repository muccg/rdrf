import sys
from django.core.management import BaseCommand
from django.db import transaction
from rdrf.models.definition.models import Registry, CommonDataElement, CDEPermittedValueGroup, CDEPermittedValue
from rdrf.models.proms.models import Survey, SurveyQuestion, Precondition, RegistryForm, Section
from rdrf.services.io.defs.importer import Importer


class Command(BaseCommand):
    help = "Setup PROMS system: preserve metadata(optional), clear existing models, import yaml"

    def add_arguments(self, parser):
        parser.add_argument('-y',
                            '--yaml-file',
                            action='store',
                            dest='yaml',
                            default=None,
                            help='The registry definition yaml file')
        parser.add_argument('-o',
                            '--override-metadata',
                            action='store',
                            dest='override',
                            default='N',
                            help='Y to override metadata with metadata in yaml. importer preserves metadata by default')

    def handle(self, *args, **options):
        yaml_file = options.get("yaml")
        override_metadata = options.get("override").upper()

        if yaml_file is None:
            self.stderr.write(f"Error: --yaml argument is required")
            sys.exit(1)
            return

        with open(yaml_file) as import_file:
            registry_import_data = import_file.read()
            importer = Importer()
            importer.load_yaml_from_string(registry_import_data)

            current_metadata = None
            try:
                registry = Registry.objects.get(code=importer.data['code'])
            except Registry.DoesNotExist:
                pass
            else:
                if override_metadata == 'N':  # preserve metadata by default
                    current_metadata = registry.metadata_json

            klasses = [CommonDataElement, CDEPermittedValueGroup, CDEPermittedValue, Survey,
                       SurveyQuestion, Precondition, RegistryForm, Section]

            with transaction.atomic():
                for klass in klasses:
                    klass.objects.all().delete()

                try:
                    importer.create_registry()
                except Exception as e:
                    self.stderr.write("Exception %s" % e)
                    raise e
                else:
                    self.stdout.write("No exception was caught in the importer")

                self.stdout.write("Importer state: %s" % importer.state)
                self.stdout.write("Importer errors: %s" % importer.errors)

                if override_metadata == 'N' and current_metadata is not None:
                    registry.metadata_json = current_metadata

                registry.save()
