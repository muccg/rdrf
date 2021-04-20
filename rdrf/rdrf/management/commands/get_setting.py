import sys
import json
from django.conf import settings
from django.core.management import BaseCommand
from rdrf.models.definition.models import Registry
from ccg_django_utils.conf import EnvConfig


class Command(BaseCommand):
    help = "Get a setting value: env | metadata | settings"

    def add_arguments(self, parser):
        parser.add_argument("-c",
                            "--code",
                            action="store",
                            dest="registry_code",
                            default=None,
                            help="The registry code")
        parser.add_argument("-t",
                            "--type",
                            action="store",
                            dest="setting_type",
                            default=None,
                            help="env | metadata | settings")
        parser.add_argument("-n"
                            "--name",
                            action="store",
                            dest="setting_name",
                            default=None,
                            help="The setting variable name")

    def handle(self, *args, **options):
        registry_code = options.get("registry_code")
        setting_type = options.get("setting_type")
        setting_name = options.get("setting_name")

        registry = None
        try:
            registry = Registry.objects.get(code=registry_code)
        except Registry.DoesNotExist:
            self.stderr.write(f"Error: Unknown registry code: {registry_code}")
            sys.exit(1)
            return

        if registry is not None:
            result = ""
            if setting_type == 'metadata':
                metadata = json.loads(registry.metadata_json)
                if setting_name in metadata.keys():
                    result = str(metadata[setting_name])
            elif setting_type == 'settings':
                if hasattr(settings, setting_name):
                    result = str(getattr(settings, setting_name))
            elif setting_type == 'env':
                env = EnvConfig()
                result = env.get(setting_name, "Not found")
            self.stdout.write(result)
