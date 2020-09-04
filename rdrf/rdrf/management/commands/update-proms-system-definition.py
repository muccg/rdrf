import sys
from django.core.management.base import BaseCommand
from rdrf.models.definition.models import Registry

from rdrf.services.rest.views.proms_api import PromsSystemManager


class Command(BaseCommand):
    help = 'Syncs the definition from this site system to the associated proms system'

    def add_arguments(self, parser):
        parser.add_argument('-c',
                            '--code',
                            action='store',
                            dest='code',
                            default=None,
                            help='The registry code on the site system')
        parser.add_argument('-o',
                            '--overwrite-metadata',
                            action='store_true',
                            dest='override',
                            default=False,
                            help='To overwrite proms system metadata with site system metadata. Skip this option to preserve metadata.')

    def handle(self, *args, **options):
        override = options.get("override")
        code = options.get("code")

        if code is None:
            self.stderr.write(f"Error: --code argument is required")
            sys.exit(1)
            return

        try:
            registry_model = Registry.objects.get(code=code)
        except Registry.DoesNotExist:
            self.stderr.write(f"{code} does not exist")
        else:
            if registry_model.proms_system_url:
                proms_manager = PromsSystemManager(registry_model)
                proms_manager.update_definition(override_metadata=override)
