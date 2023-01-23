from django.core.management.base import BaseCommand
from dashboards.models import VisualisationBaseDataConfig
from dashboards.data import RegistryDataFrame
from datetime import datetime


class Command(BaseCommand):
    help = "Generate Visualisation Dataframe JSON"

    def print(self, msg):
        t = datetime.now()
        self.stdout.write(f"{t} visualisation base data config: {msg}" + "\n")

    def handle(self, *args, **options):
        for config in VisualisationBaseDataConfig.objects.all():
            self.print(f"generating json data for {config.registry.code}")
            rdf = RegistryDataFrame(config.registry, config, None, force_reload=True)
            json_data = rdf.data.to_json()
            config.data = json_data
            config.state = "D"
            config.save()
            self.print("saved OK")
