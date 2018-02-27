from django.core.management.base import BaseCommand
from rdrf.models.definition.models import Registry
from registry.patients.models import Patient
from rdrf.forms.progress.form_progress import FormProgress

import sys


class Command(BaseCommand):
    help = "Recalculates form progress for all patients"

    def add_arguments(self, parser):
        parser.add_argument("registry_code")

    def handle(self, registry_code, **options):
        self.registry_model = None
        try:
            self.registry_model = Registry.objects.get(code=registry_code)
        except Registry.DoesNotExist:
            self.stderr.write("Error: Unknown registry code: %s" %
                              registry_code)
            sys.exit(1)
            return

        if self.registry_model is not None:
            self._update_progress()
            self.stdout.write("Progress recalculated OK")

    def _update_progress(self):
        form_progress = FormProgress(self.registry_model)

        for patient_model in Patient.objects.filter(rdrf_registry__in=[self.registry_model]):
            if not self.registry_model.has_feature("contexts"):
                default_context = patient_model.default_context(
                    self.registry_model)
                form_progress.save_for_patient(patient_model, default_context)
                self.stdout.write("Recalculated progress for Patient %s" % patient_model.pk)

            else:
                self.stderr.write(
                    "Script does not support registries with multiple contexts allowed, yet")
                sys.exit(1)
