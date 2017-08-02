import sys
from datetime import datetime, timedelta
from django.core.management import BaseCommand
from rdrf.models import Registry
from registry.groups.models import CustomUser
from registry.patients.models import Patient
from registry.patients.models import ParentGuardian

class Command(BaseCommand):
    help = "Lists users who haven't logged in for a while"

    def add_arguments(self, parser):
        parser.add_argument('-r',"--registry_code",
                            action='store',
                            dest='registry_code',
                            help='Code of registry to check')

        parser.add_argument("-d", "--days",
                            action="store",
                            dest="days",
                            help="Number of days since last login.")
        
    def _print(self, msg):
        self.stdout.write(msg + "\n")

    def _get_numdays(self, registry_model):
        metadata = registry_model.metadata
        if "reminders" in metadata:
            reminder_dict = metadata["reminders"]
            last_login_days = reminder_dict.get("last_login_days", 365)
            return last_login_days
        else:
            return 365

    def _get_threshold(self, num_days):
        return datetime.now() - timedelta(days=num_days)

    def handle(self, *args, **options):
        registry_code = options.get("registry_code", None)
        if registry_code is None:
            self._print("Registry code required")
            sys.exit(1)

        try:
            registry_model = Registry.objects.get(code=registry_code)
        except Registry.DoesNotExist:
            self._print("Registry does not exist")
            sys.exit(1)

        days = options.get("days", None)
        # allow override form command line else use registry config
        if days is None:
            days = self._get_numdays(registry_model)

        threshold = self._get_threshold(days)
            
        for user in self._get_users(registry_model):
            if user.last_login is None or user.last_login < threshold:
                print(user.username)


    def _get_users(self, registry_model):
        for user in CustomUser.objects.filter(registry__in=[registry_model],
                                              is_active=True):
            if user.is_patient or user.is_parent:
                yield user
            
