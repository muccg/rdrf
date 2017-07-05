from django.core.management import BaseCommand
from rdrf.models import Registry
from rdrf.models import Modjgo
import yaml
import jsonschema

explanation = "to do"

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
        self.schemas = self._load_schema_file()
        collection = options.get("collection", "cdes")

        for modjgo_model in Modjgo.objects.filter(collection=collection):
            data = modjgo_model.data
            problems = self._check_for_problems(data, collection)


    def _load_schema_file(self):
        modjgo_schema_file = "/app/rdrf/rdrf/schemas/modjgo.yaml"
        with open(modjgo_schema_file) as sf:
            return yaml.load(sf)

    def _get_schema(self, collection):
        return self.schemas[collection]

    def _check_for_problems(self, data, collection):
        schema = self._get_schema(collection)
        jsonschema.validate({collection: data}, schema)
        

        
        

        
        
        
