from django.core.management.base import BaseCommand
from rdrf.models.definition.models import Registry

from rdrf.services.rest.views.proms_api import PromsSystemManager


class Command(BaseCommand):
    help = 'Pulls proms from associated proms system'

    def handle(self, *args, **options):
        for registry_model in Registry.objects.all():
            if registry_model.proms_system_url:
                proms_manager = PromsSystemManager(registry_model)
                proms_manager.download_proms()
