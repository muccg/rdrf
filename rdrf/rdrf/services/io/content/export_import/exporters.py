from collections import defaultdict, OrderedDict
import os
from django.core import serializers
from django.apps import apps

from .utils import DelegateMixin
from .utils import app_schema_version
from .utils import file_checksum
from .utils import maybe_indent
from functools import reduce


class DataGroupExporter(DelegateMixin):
    """Exports a group of data like "Reference Data", "CDEs", etc."""

    def __init__(self, dfn, exporters_catalogue, logger):
        DelegateMixin.__init__(self, delegate_to=dfn)
        self.exporters_catalogue = exporters_catalogue
        self.model_exporters = exporters_catalogue.models
        self.datagroup_exporters = exporters_catalogue.datagroups
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

        child_logger = maybe_indent(self.logger)
        child_context = self.exporter_context.copy()
        child_context['workdir'] = self.workdir

        for dg in self.datagroups:
            exporter = self.datagroup_exporters.get(dg)(
                dg, self.exporters_catalogue, child_logger)
            if exporter.export(**child_context):
                self.meta['data_groups'].append(exporter.get_meta_info())

        for model_name in self.models:
            exporter = self.model_exporters.get(
                apps.get_model(model_name))(
                model_name, child_logger)
            if exporter.export(**child_context):
                self.meta['models'].append(exporter.get_meta_info())

        return True

    def get_meta_info(self, top_level=False):
        if self.meta is None:
            raise ValueError('Invalid state: Data Group needs to be exported first')

        app_versions = None
        if top_level:
            models = self.collect_all_models(self)

            def app_label(m):
                return m.split('.', 1)[0]

            apps = set(map(app_label, models))
            app_versions = {app: app_schema_version(app) for app in apps}

        return OrderedDict(omit_empty((
            ('name', self.name),
            ('dir_name', self.dirname),
            ('app_versions', app_versions),
            ('data_groups', self.meta['data_groups']),
            ('models', self.meta['models']),
        )))

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
            raise ValueError(
                'Invalid state: Model %s needs to be exported first' %
                self.full_modelname)
        return self.meta_collector.collect()


class BaseMetaInfo(DelegateMixin):

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
            return reduce(lambda count, _: count + 1, gen, 0)

        with open(self.full_filename) as data:
            count = count_generator_items(serializers.deserialize(self.format, data))
            return count


def omit_empty(xs):
    return [x for x in xs if x[1]]
