from bson.json_util import dumps, loads
from collections import defaultdict, OrderedDict
import hashlib
import logging
import os
from django.core import serializers
from django.apps import apps

from rdrf.utils import mongo_db_name
from rdrf.mongo_client import construct_mongo_client
from .utils import DelegateMixin, IndentedLogger, maybe_indent, file_checksum, app_schema_version


class DataGroupExporter(object, DelegateMixin):
    """Exports a group of data like "Reference Data", "CDEs", etc."""

    def __init__(self, dfn, exporters_catalogue, logger):
        DelegateMixin.__init__(self, delegate_to=dfn)
        self.exporters_catalogue = exporters_catalogue
        self.model_exporters = exporters_catalogue.models
        self.datagroup_exporters = exporters_catalogue.datagroups
        self.mongo_collection_exporters = exporters_catalogue.mongo_collections
        self.logger = logger
        self.exporter_context = {}

        self.meta = None
        self.exported_at = None

    @property
    def workdir(self):
        return os.path.join(self.parent_workdir, self.dirname)

    def export(self, **kwargs):
        self.exporter_context = kwargs
        self.parent_workdir = self.exporter_context['workdir']
        os.makedirs(self.workdir)
        self.meta = defaultdict(list)
        self.logger.debug("Exporting datagroup '%s' to '%s'", self.name, self.workdir)

        child_logger = maybe_indent(self.logger)
        child_context = self.exporter_context.copy()
        child_context['workdir'] = self.workdir

        # TODO there is some further abstraction in the similar looking 3
        # parts below
        if len(self.datagroups) > 0:
            self.logger.debug("Exporting %d nested datagroups" % len(self.datagroups))
        for dg in self.datagroups:
            exporter = self.datagroup_exporters.get(dg)(dg, self.exporters_catalogue, child_logger)
            if exporter.export(**child_context):
                self.meta['data_groups'].append(exporter.get_meta_info())

        if len(self.models) > 0:
            self.logger.debug("Exporting %d models" % len(self.models))
        for model in self.models:
            exporter = self.model_exporters.get(model)(model, child_logger)
            if exporter.export(**child_context):
                self.meta['models'].append(exporter.get_meta_info())

        if len(self.collections) > 0:
            self.logger.debug("Exporting %d models" % len(self.collections))
        for collection in self.collections:
            exporter = self.mongo_collection_exporters.get(collection)(collection, child_logger)
            if exporter.export(**child_context):
                self.meta['collections'].append(exporter.get_meta_info())
        return True

    def get_meta_info(self, top_level=False):
        if self.meta is None:
            raise ValueError('Invalid state: Data Group needs to be exported first')

        app_versions = None
        if top_level:
            models = self.collect_all_models(self)
            app_label = lambda m: m.split('.', 1)[0]
            apps = set(map(app_label, models))
            app_versions = dict([(app, app_schema_version(app)) for app in apps])

        return OrderedDict(omit_empty((
            ('name', self.name),
            ('dir_name', self.dirname),
            ('app_versions', app_versions),
            ('data_groups', self.meta['data_groups']),
            ('models', self.meta['models']),
            ('collections', self.meta['collections']),)))

    def collect_all_models(self, dfn):
        """Collects all the model names exported by these data groups recursively."""
        models = set(dfn.models)
        for datagroup in dfn.datagroups:
            models = models.union(self.collect_all_models(datagroup))
        return models


class ModelExporter(object):
    def __init__(self, model_name, logger):
        self.model_name = model_name
        self.model = apps.get_model(self.model_name)
        self.logger = logger
        self.meta_collector = ModelMetaInfo(self, maybe_indent(logger))
        self.exporter_context = {}
        self.export_finished = False
        self.format = 'json'

    @property
    def queryset(self):
        return self.model.objects.all()

    @property
    def full_filename(self):
        return os.path.join(self.workdir, self.filename)

    @property
    def full_modelname(self):
        return '%s.%s' % (self.model.__module__, self.model.__name__)

    def export(self, **kwargs):
        self.exporter_context = kwargs
        self.workdir = self.exporter_context['workdir']
        self.filename = '%s.%s' % (self.model._meta.db_table, self.format)

        self.logger.debug("Exporting model '%s' to '%s'", self.full_modelname, self.full_filename)

        with open(self.full_filename, 'w') as out:
            serializers.serialize(self.format, self.queryset,
                use_natural_primary_keys=True,
                use_natural_foreign_keys=True,
                indent=2,
                stream=out)
        self.export_finished = True
        return True

    def get_meta_info(self):
        if not self.export_finished:
            raise ValueError('Invalid state: Model %s needs to be exported first' % self.full_modelname)
        return self.meta_collector.collect()

class MongoCollectionExporter(object):
    def __init__(self, collection_name, logger):
        self.logger = logger
        self.meta_collector = CollectionMetaInfo(self, maybe_indent(logger))
        self.client = construct_mongo_client()
        self.collection_name = collection_name
        self.filename = collection_name
        self.exporter_context = {}
        if '.' not in self.filename:
            self.filename += '.bson'
        self.export_finished = False

    @property
    def full_filename(self):
        return os.path.join(self.workdir, self.filename)

    def export(self, **kwargs):
        self.exporter_context = kwargs
        self.workdir = self.exporter_context['workdir']
        registry_code = self.exporter_context['registry_code']
        db = self.client[mongo_db_name(registry_code)]
        if self.collection_name not in db.collection_names():
            self.logger.info("Collection '%s' doesn't exist for registry '%s'. Ignoring it."
                % (self.collection_name, registry_code))
            return False
        collection = db[self.collection_name]

        self.logger.debug("Exporting Mongo collection '%s' to '%s'", self.collection_name, self.full_filename)

        with open(self.full_filename, 'w') as out:
            out.write(dumps(list(collection.find()), indent=2))
        self.export_finished = True
        return True

    def get_meta_info(self):
        if not self.export_finished:
            raise ValueError('Invalid state: Collection %s needs to be exported first' % self.collection_name)
        return self.meta_collector.collect()


class BaseMetaInfo(object, DelegateMixin):
    def __init__(self, exporter, logger):
        DelegateMixin.__init__(self, delegate_to=exporter)
        self.logger = logger

    def collect(self):
        return {
            'file_name': self.filename,
            'object_count': self.count_objects_in_file(),
            'md5_checksum': file_checksum(self.full_filename),
        }

    def count_objects_in_file(self):
        raise NotImplementedError()


class ModelMetaInfo(BaseMetaInfo):
    def collect(self):
        d = {
            'model_name': self.model_name,
            'model_class': self.full_modelname,
        }
        d.update(BaseMetaInfo.collect(self))
        return d

    def count_objects_in_file(self):
        def count_generator_items(gen):
            return reduce(lambda count, _: count+1, gen, 0)

        with open(self.full_filename) as data:
            count = count_generator_items(serializers.deserialize(self.format, data))
            self.logger.debug('exported %d object(s)', count)
            return count


class CollectionMetaInfo(BaseMetaInfo):
    def collect(self):
        d = {'collection_name': self.collection_name}
        d.update(BaseMetaInfo.collect(self))
        return d

    def count_objects_in_file(self):
        with open(self.full_filename) as data:
            count = len(loads(data.read()))
            self.logger.debug('exported %d object(s)', count)
            return count


def omit_empty(xs):
    return filter(lambda x: x[1], xs)
