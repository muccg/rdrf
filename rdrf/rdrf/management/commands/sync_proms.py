from django.core.management.base import BaseCommand
from rdrf.models.definition.models import Registry

from rdrf.services.rest.views.proms_api import PromsProcessor


class Command(BaseCommand):
    help = 'Syncs the definition from this site system to the associated proms system'

    def add_arguments(self, parser):
        parser.add_argument('-o',
                            '--overwrite-metadata',
                            action='store_true',
                            dest='override',
                            default=False,
                            help='To overwrite proms system metadata with site system metadata. Skip this option to preserve metadata.')

    def handle(self, *args, **options):
        for registry_model in Registry.objects.all():
            if registry_model.proms_system_url:
                proms_processor = PromsProcessor(registry_model)
                proms_processor.sync_proms()
