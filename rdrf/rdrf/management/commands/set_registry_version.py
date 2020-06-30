import sys
from django.core.management import BaseCommand
from rdrf.models.definition.models import Registry


class Command(BaseCommand):
    help = "Set the registry version"

    def add_arguments(self, parser):
        parser.add_argument('-c',
                            '--code',
                            action='store',
                            dest='code',
                            default=None,
                            help='The registry code')
        parser.add_argument('--ver',
                            action='store',
                            dest='version',
                            default=None,
                            help='The new registry version to be set')

    def handle(self, *args, **options):
        registry_code = options.get("code")
        version = options.get("version")

        registry = None
        try:
            registry = Registry.objects.get(code=registry_code)
        except Registry.DoesNotExist:
            self.stderr.write(f"Error: Unknown registry code: {registry_code}")
            sys.exit(1)
            return

        if registry is not None:
            registry.version = version
            registry.save()
