from django.core.management import BaseCommand
from rdrf.models.definition.models import Registry
from registry.patients.models import Patient
from rdrf.services.tasks import check_proms


class Command(BaseCommand):
    help = "Check each patient to see if they have proms requests that need sending."

    def handle(self, *args, **options):
        for registry_model in Registry.objects.all():
            if registry_model.has_feature("proms_clinical"):
                for patient in Patient.objects.filter(
                    rdrf_registry__in=[registry_model], date_of_death__isnull=True
                ):
                    print(f"checking proms for {patient}")
                    check_proms.delay(registry_model.code, patient.id)
