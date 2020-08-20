import sys
from django.core.management import BaseCommand
from django.db import transaction
from rdrf.models.definition.models import Registry
from rdrf.services.io.defs.importer import Importer


class Command(BaseCommand):
    help = "Setup PROMS system: overwrite metadata(optional), clear existing models, import yaml. " \
           "(Preserves metadata by default.)"

    def add_arguments(self, parser):
        parser.add_argument('-y',
                            '--yaml-file',
                            action='store',
                            dest='yaml',
                            default=None,
                            help='The registry definition yaml file')
        parser.add_argument('-o',
                            '--overwrite-metadata',
                            action='store_true',
                            dest='override',
                            default=False,
                            help='To overwrite metadata with metadata in yaml. Skip this option to preserve metadata.')

    def handle(self, *args, **options):
        yaml_file = options.get("yaml")
        override_metadata = options.get("override")

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
                if not override_metadata:  # preserve metadata by default
                    current_metadata = registry.metadata_json

            with transaction.atomic():
                try:
                    importer.create_registry()
                    if not override_metadata and current_metadata is not None:  # restore metadata
                        registry = Registry.objects.get(code=importer.data['code'])
                        registry.metadata_json = current_metadata
                        try:
                            registry.save()
                        except Exception as e:
                            self.stderr.write("Exception while saving registry: %s" % e)
                            raise e
                except Exception as e:
                    self.stderr.write("Exception %s" % e)
                    raise e

                self.stdout.write("Importer state: %s" % importer.state)
                self.stdout.write("Importer errors: %s" % importer.errors)
