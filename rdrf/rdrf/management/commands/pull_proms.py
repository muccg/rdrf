from django.core.management.base import BaseCommand
from django.db import transaction
from rdrf.models.definition.models import Registry
from rdrf.models.proms.models import SurveyRequest
from registry.patients.models import Patient

from rdrf.services.rest.views.proms_api import PromsProcessor


class Command(BaseCommand):
    help = 'Pulls proms from associated proms system'

    def handle(self, *args, **options):
        for registry_model in Registry.objects.all():
            if registry_model.proms_system_url:
                proms_processor = PromsProcessor(registry_model)
                proms_processor.download_proms()
