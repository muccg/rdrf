from django.core.management import BaseCommand
from rdrf.models.definition.models import Registry
from rdrf.models.proms.models import SurveyAssignment, SurveyRequest
from rdrf.models.task_models import CustomActionExecution
from registry.groups.models import CustomUser
from registry.patients.models import Patient
from useraudit.models import FailedLoginLog, LoginAttempt, LoginLog

import json

class Command(BaseCommand):
    help = "Gets stats for every registry on the site"

    def handle(self, *args, **options):
        statblock = {"stats": []}
        for registry_model in Registry.objects.all():
            registry_code = registry_model.code
            assignment_count = SurveyAssignment.objects.filter(registry__in=[registry_model]).count()
            request_count = SurveyRequest.objects.filter(registry__in=[registry_model]).count()
            patient_count = Patient.objects.filter(rdrf_registry__in=[registry_model]).count()

            registry_users = [reguser.username for reguser in CustomUser.objects.all() if registry_model in reguser.registry.all()]
            user_count = len(registry_users)
            attempt_count = LoginAttempt.objects.filter(username__in=registry_users).count()
            login_count = LoginLog.objects.filter(username__in=registry_users).count()
            failure_count = FailedLoginLog.objects.filter(username__in=registry_users).count()

            cae_count = CustomActionExecution.objects.filter(custom_action_code__in=[ca.code for ca in registry_model.customaction_set.all()]).count()

            registry_block = {
                "RegistryCode": registry_code,
                "SurveyAssignment": assignment_count,
                "SurveyRequest": request_count,
                "Patient": patient_count,
                "User": user_count,
                "LoginAttempt": attempt_count,
                "LoginLog": login_count,
                "FailedLoginLog": failure_count,
                "CustomActionExecution": cae_count
            }

            statblock["stats"].append(registry_block)

        print(json.dumps(statblock))
