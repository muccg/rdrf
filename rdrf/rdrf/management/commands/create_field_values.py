from django.core.management import BaseCommand
from rdrf.models.definition.models import Registry
from registry.patients.models import Patient
from explorer.models import FieldValue
from explorer.utils import create_field_values


class Command(BaseCommand):
    """
    (re)-create field values for reporting
    """
    help = "Creates field values for reporting"

    def handle(self, *args, **options):
        for registry_model in Registry.objects.all():
            FieldValue.objects.filter(registry=registry_model).delete()
            for patient_model in Patient.objects.filter(rdrf_registry__in=[registry_model]):
                for context_model in patient_model.context_models:
                    if context_model.registry.code == registry_model.code:
                        create_field_values(registry_model,
                                            patient_model,
                                            context_model)
