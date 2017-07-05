from django.core.management import BaseCommand
from rdrf.models import Registry
from rdrf.models import Modjgo
import yaml
import jsonschema

explanation = "This command checks for schema validation errors"

class Command(BaseCommand):
    help = 'Checks in clinical db against json schema(s)'

    def add_arguments(self, parser):
        parser.add_argument('--collection',
                            action='store',
                            dest='collection',
                            default="cdes",
                            help='Collection name ( one of cdes, history or registry_specific)')

    def _usage(self):
        print(explanation)

    def handle(self, *args, **options):
        self.schema = self._load_schema()
        collection = options.get("collection", "cdes")

        for modjgo_model in Modjgo.objects.filter(collection=collection):
            data = modjgo_model.data
            problem = self._check_for_problem(collection, data)
            if problem is not None:
                django_model, django_id, message = problem
                print("%s/%s : %s" % (django_model,
                                      django_id,
                                      message))
                
    def _load_schema(self):
        modjgo_schema_file = "/app/rdrf/rdrf/schemas/modjgo.yaml"
        with open(modjgo_schema_file) as sf:
            return yaml.load(sf)

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
