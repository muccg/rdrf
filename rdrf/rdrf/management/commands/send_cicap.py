import sys
from django.core.management.base import BaseCommand
from django.conf import settings
from rdrf.models.definition.models import Registry
from rdrf.services.io.actions import deidentified_data_extract as dde


class Command(BaseCommand):
    help = 'Send deidentified data to CICAP'
    def add_arguments(self, parser):
        parser.add_argument('-r',
                            '--registry-code',
                            action='store',
                            dest='registry_code',
                            default=None,
                            help='registry code')

    def handle(self, *args, **options):
        if hasattr(settings, "CICAP_ADDRESS"):
            cicap_address = settings.CICAP_ADDRESS
        else:
            cicapp_address = None

        if not cicapp_address:
            self.stderr("CICAP_ADDRESS is not configured")
            sys.exit(1)
            
        registry_code = options.registry_code

        if registry_code is None:
            self.stderr.write(f"Error: --registry-code argument is required")
            sys.exit(1)

        try:
            registry_model = Registry.objects.get(code=registry_code)
        except Registry.DoesNotExist:
            self.stderr.write(f"{registry_code} does not exist")
            sys.exit(1)

        


        


