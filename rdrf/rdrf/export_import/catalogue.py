from collections import defaultdict
from .exporters import DataGroupExporter, ModelExporter
from .importers import DataGroupImporter, ModelImporter


class Catalogue(object):

    def __init__(self):
        self._catalogue = defaultdict(lambda: self.factory)

    def register(self, obj, exporter):
        self._catalogue[obj] = exporter

    def get(self, obj):
        return self._catalogue[obj]

    def get_instance(self, obj, *args):
        if not args:
            args = [obj]
        return self.get(obj)(*args)


class ModelExporterCatalogue(Catalogue):
    factory = ModelExporter


class DataGroupExporterCatalogue(Catalogue):
    factory = DataGroupExporter


class DataGroupImporterCatalogue(Catalogue):
    factory = DataGroupImporter


class ModelImporterCatalogue(Catalogue):
    factory = ModelImporter
