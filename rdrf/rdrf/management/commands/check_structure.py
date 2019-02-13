import sys
from django.core.management import BaseCommand
from rdrf.models.definition.models import Registry
from rdrf.models.definition.models import ClinicalData
import yaml
import jsonschema
import errno
import os

explanation = "This command checks for schema validation errors"
SCHEMA_FILE = "modjgo.yaml"


class Command(BaseCommand):
    help = 'Checks in clinical db against json schema(s)'

    def add_arguments(self, parser):
        parser.add_argument('-r', "--registry_code",
                            action='store',
                            dest='registry_code',
                            help='Code of registry to check')
        parser.add_argument('-c', '--collection',
                            action='store',
                            dest='collection',
                            default="cdes",
                            choices=['cdes', 'history', 'progress', 'registry_specific'],
                            help='Collection name')

    def _usage(self):
        print(explanation)

    def _print(self, msg):
        self.stdout.write(msg + "\n")

    def handle(self, *args, **options):
        problem_count = 0
        self.schema = self._load_schema()
        registry_code = options.get("registry_code", None)
        if registry_code is None:
            self._print("Error: registry code required")
            sys.exit(1)
        try:
            Registry.objects.get(code=registry_code)
        except Registry.DoesNotExist:
            self._print("Error: registry does not exist")
            sys.exit(1)

        collection = options.get("collection", "cdes")
        if collection == "registry_specific":
            collection = "registry_specific_patient_data"

        for modjgo_model in ClinicalData.objects.filter(registry_code=registry_code,
                                                        collection=collection):
            data = modjgo_model.data
            problem = self._check_for_problem(collection, data)
            if problem is not None:
                problem_count += 1
                django_model, django_id, message = problem
                self._print("%s;%s;%s;%s" % (modjgo_model.pk,
                                             django_model,
                                             django_id,
                                             message))

        if problem_count > 0:
            sys.exit(1)

    def _load_schema(self):
        cmd_dir = os.path.dirname(__file__)
        schema_path = os.path.abspath(os.path.join(cmd_dir,
                                                   "..",
                                                   "..",
                                                   "db",
                                                   "schemas",
                                                   SCHEMA_FILE))

        if os.path.exists(schema_path):
            with open(schema_path) as sf:
                return yaml.load(sf)

        raise FileNotFoundError(errno.ENOENT,
                                os.strerror(errno.ENOENT),
                                SCHEMA_FILE)

    def _get_key(self, data, key):
        if data is None:
            return None
        if key in data:
            return data[key]

    def _check_for_problem(self, collection, data):
        schema = self._load_schema()
        try:
            jsonschema.validate({collection: data}, schema)
            return None
        except Exception as verr:
            message = verr.message
            django_id = self._get_key(data, "django_id")
            django_model = self._get_key(data, "django_model")
            return django_model, django_id, message
