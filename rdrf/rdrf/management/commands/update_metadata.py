import sys
import json
from django.core.management import BaseCommand
from rdrf.models.definition.models import Registry


class Command(BaseCommand):
    help = "Update the registry metadata for a particular key"

    def add_arguments(self, parser):
        parser.add_argument('-c',
                            '--code',
                            action='store',
                            dest='code',
                            default=None,
                            help='The registry code')
        parser.add_argument('-k',
                            '--key',
                            action='store',
                            dest='key',
                            default=None,
                            help='The metadata key')
        parser.add_argument('--value',
                            action='store',
                            dest='value',
                            default=None,
                            help='The metadata value')

    def handle(self, *args, **options):
        registry_code = options.get("code")
        metadata_key = options.get("key")
        metadata_value = options.get("value")

        registry = None
        try:
            registry = Registry.objects.get(code=registry_code)
        except Registry.DoesNotExist:
            self.stderr.write(f"Error: Unknown registry code: {registry_code}")
            sys.exit(1)
            return

        if registry is not None:
            metadata = json.loads(registry.metadata_json)
            metadata[metadata_key] = metadata_value
            registry.metadata_json = json.dumps(metadata)
            registry.save()
