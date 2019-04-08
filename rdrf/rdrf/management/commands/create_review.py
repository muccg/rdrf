import sys
from django.core.management import BaseCommand
explanation = "This command creates a Patient Review"


class Command(BaseCommand):
    help = 'Create a Patient review'

    def add_arguments(self, parser):
        parser.add_argument('-r', "--registry-code",
                            action='store',
                            dest='registry_code',
                            help='Registry code containing Review')
        parser.add_argument('-rc', '--review-code',
                            action='store',
                            dest='review_code',
                            help='Review code')
        parser.add_argument('-pid', '--patient-id',
                            action='store',
                            dest='patient_id',
                            help='Patient ID')

    def _usage(self):
        print(explanation)

    def _print(self, msg):
        self.stdout.write(msg + "\n")

    def handle(self, *args, **options):
        from registry.patients.models import Patient
        from rdrf.models.definition.models import Registry
        from rdrf.models.definition.review_models import Review
        from rdrf.models.definition.review_models import PatientReview

        registry_code = options.get("registry_code", None)
        if registry_code is None:
            self._print("Error: registry code required")
            sys.exit(1)
        try:
            registry_model = Registry.objects.get(code=registry_code)
        except Registry.DoesNotExist:
            self._print("Error: registry does not exist")
            sys.exit(1)

        patient_id = options.get("patient_id", None)
        if patient_id is None:
            self._print("Error: patient id required")
            sys.exit(1)

        try:
            patient_model = Patient.objects.get(id=int(patient_id))
        except Patient.DoesNotExist:
            self._print("Error: patient id does not exist")
            sys.exit(1)

        review_code = options.get("review_code", None)
        if review_code is None:
            self._print("Error: review code required")
            sys.exit(1)
        
        try:
            review_model = Review.objects.get(registry=registry_model,
                                              code=review_code)
        except Review.DoesNotExist:
            self._print("Error: review does not exist")
            sys.exit(1)

        default_context = patient_model.default_context(registry_model)
        if default_context is None:
            self._print("Error: default context could not be determined")
            sys.exit(1)
        
        pr = PatientReview(review=review_model,
                           patient=patient_model,
                           context=default_context)

        pr.save()
        pr.create_review_items()
        
                           
                           

            
            

        

        
