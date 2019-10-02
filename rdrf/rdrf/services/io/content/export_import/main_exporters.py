from collections import OrderedDict
from datetime import datetime
import json
import logging
import os
import shutil
import tempfile

from rdrf.models.definition.models import Registry
from .definitions import REGISTRY_DEF_EXPORT_DEFINITION, REGISTRY_WITH_DATA_EXPORT_DEFINITION
from .utils import IndentedLogger

logger = logging.getLogger(__name__)

# test


class TopLevelExporter(object):

    def __init__(self, dfns=None):
        self.dfns = dfns
        self.tmpdir = None
        self.meta = None
        self.exported_at = None
        self._zip_file = None
        self.export_context = {}

    @property
    def workdir(self):
        return self.tmpdir

    @property
    def zip_file(self):
        return self._zip_file or 'exported_data.zip'

    def export(self, filename=None, verbose=False, indented_logs=True):
        if filename is not None:
            self._zip_file = filename
        logger = logging.getLogger(__name__)
        if verbose:
            logger.setLevel(logging.DEBUG)
        child_logger = logger
        if indented_logs:
            child_logger = IndentedLogger(logger)

        self.create_working_dir()
        self.meta = []

        self.export_context.update({
            'workdir': self.workdir,
        })

        # TODO this code is the same as first section in exporters.DataGroupExporters.export
        datagroup_exporters = self.dfns.exporters_catalogue.datagroups
        for dg in self.dfns.datagroups:
            exporter = datagroup_exporters.get(dg)(
                dg, self.dfns.exporters_catalogue, logger=child_logger)
            if exporter.export(**self.export_context):
                self.meta.append(exporter.get_meta_info(top_level=True))
        self.exported_at = datetime.now()

        self.write_out_meta_info()

        self.zip_it()

        self.remove_working_dir()

        return self.zip_file

    def get_specific_meta_info(self):
        return OrderedDict()

    def get_meta_info(self):
        if self.meta is None:
            raise ValueError('Invalid state: export() must be called first')

        meta_info = OrderedDict((('type', self.dfns.type.name),))
        meta_info.update(self.get_specific_meta_info())
        meta_info.update(OrderedDict((
            ('exported_at', self.exported_at),
            ('data_groups', self.meta))))
        return meta_info

    def write_out_meta_info(self):
        with open(os.path.join(self.workdir, 'META'), 'w') as f:
            def handler(obj):
                if hasattr(obj, 'isoformat'):
                    return obj.isoformat()
                return json.JSONEncoder().default(obj)
            json.dump(self.get_meta_info(), f, default=handler, indent=2)

    def zip_it(self):
        filename, ext = os.path.splitext(self.zip_file)
        if ext != '.zip':
            raise ValueError("Invalid extension '%s' set on zip_file. Should be '.zip'" % ext)
        shutil.make_archive(filename, 'zip', self.tmpdir)

    def create_working_dir(self):
        self.tmpdir = tempfile.mkdtemp(suffix='export')
        if self.tmpdir != self.workdir:
            os.makedirs(self.workdir)

    def remove_working_dir(self):
        shutil.rmtree(self.tmpdir)


class RegistryDefExporter(TopLevelExporter):

    def __init__(self, *args, **kwargs):
        kwargs['dfns'] = REGISTRY_DEF_EXPORT_DEFINITION
        TopLevelExporter.__init__(self, *args, **kwargs)

    def export(self, registry_code, **kwargs):
        self.registry_code = registry_code
        self.export_context['registry_code'] = registry_code
        TopLevelExporter.export(self, **kwargs)
        logger.info("Registry '%s' exported to '%s'", self.registry_code, self.zip_file)

    @property
    def workdir(self):
        return os.path.join(self.tmpdir, self.registry_code)

    @property
    def zip_file(self):
        return self._zip_file or ('exported_%s_def.zip' % self.registry_code)

    def get_specific_meta_info(self):
        registry = Registry.objects.get(code=self.registry_code)
        return OrderedDict(
            (('registry', OrderedDict((
                ('code', registry.code),
                ('name', registry.name),
                ('version', registry.version),
                ('description', registry.desc)))),
             ))


class RegistryExporter(RegistryDefExporter):

    def __init__(self, *args, **kwargs):
        kwargs['dfns'] = REGISTRY_WITH_DATA_EXPORT_DEFINITION
        TopLevelExporter.__init__(self, *args, **kwargs)

    @property
    def zip_file(self):
        return self._zip_file or ('exported_%s_with_data.zip' % self.registry_code)


class Exporter(TopLevelExporter):

    @staticmethod
    def create(dfns):
        exporter = Exporter(dfns=dfns)
        return exporter

    def export(self, **kwargs):
        TopLevelExporter.export(self, **kwargs)
        logger.info("Data exported to '%s'", self.zip_file)
