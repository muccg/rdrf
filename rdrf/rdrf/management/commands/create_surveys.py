import sys
from django.core.management import BaseCommand
explanation = "This command creates surveys"


def get_parent_user(patient_model):
    from registry.patients.models import ParentGuardian
    pgs = [pg for pg in ParentGuardian.objects.filter(patient=patient_model)]
    if len(pgs) > 0:
        pg = pgs[0]
        return pg.user
    else:
        return None


class Command(BaseCommand):
    help = explanation

    def add_arguments(self, parser):
        parser.add_argument('-r', "--registry-code",
                            action='store',
                            dest='registry_code',
                            help='Registry code containing Survey')
        parser.add_argument('-sn', '--survey-name',
                            action='store',
                            dest='survey_name',
                            help='Survey name')
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
        from rdrf.models.proms.models import Survey
        from rdrf.models.proms.models import SurveyRequest

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

        parent_user = get_parent_user(patient_model)
        if parent_user is None:
            self._print("Error no parent user for id")
            sys.exit(1)

        survey_name = options.get("survey_name", None)
        if survey_name is None:
            self._print("Error: survey name required")
            sys.exit(1)

        try:
            survey_model = Survey.objects.get(registry=registry_model,
                                              name=survey_name)

        except Survey.DoesNotExist:
            self._print("Error: survey does not exist")
            sys.exit(1)

        default_context = patient_model.default_context(registry_model)
        if default_context is None:
            self._print("Error: default context could not be determined")
            sys.exit(1)

        survey_request = SurveyRequest(registry=registry_model,
                                       patient=patient_model,
                                       survey_name=survey_model.name,
                                       state="requested",
                                       user=parent_user.username)
        survey_request.save()
        survey_request._send_proms_request()  # this creates the survey assignment
        print("patient %s token %s" % (patient_model.pk,
                                       survey_request.patient_token))
