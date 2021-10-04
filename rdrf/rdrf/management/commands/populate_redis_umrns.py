import sys
from django.core.management.base import BaseCommand
from django_redis import get_redis_connection
from registry.patients.models import Patient
from rdrf.models.definition.models import Registry


class Command(BaseCommand):
    help = 'Re-populates umrns in redis'

    def add_arguments(self, parser):
        parser.add_argument('-r', "--registry-code",
                            action='store',
                            dest='registry_code',
                            help='Registry code')

    def _print(self, msg):
        self.stdout.write(msg + "\n")

    def handle(self, *args, **kwargs):
        registry_code = kwargs.get("registry_code", None)
        if registry_code is None:
            self._print("Error: registry code required")
            sys.exit(1)
        try:
            Registry.objects.get(code=registry_code)
        except Registry.DoesNotExist:
            self._print("Error: registry does not exist")
            sys.exit(1)

        conn = get_redis_connection("blackboard")
        umrns = set(Patient.objects.filter(umrn__isnull=False).filter(
            rdrf_registry__code__exact=registry_code).values_list('umrn', flat=True))

        for umrn in umrns:
            conn.sadd(f"{registry_code}:umrns", umrn)
