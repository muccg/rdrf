import contextlib
import dateutil.parser
import json
import logging
import os
import shutil
import tempfile
from zipfile import ZipFile

from django.db import transaction

from rdrf.models.definition.models import Registry
from rdrf.db.db import reset_sql_sequences
from .catalogue import DataGroupImporterCatalogue, ModelImporterCatalogue
from .exceptions import ImportError
from .importers import get_meta_value, allow_if_forced
from . import definitions
from .utils import DelegateMixin, IndentedLogger, app_schema_version
from functools import reduce

logger = logging.getLogger(__name__)


@contextlib.contextmanager
def zipfile_contents(zipfile):
    tmpdir = tempfile.mkdtemp(suffix='import')
    archive = ZipFile(zipfile)
    archive.extractall(tmpdir)

    yield tmpdir

    shutil.rmtree(tmpdir)


class ZipFileImporter(object):

    def __init__(self, zipfile, catalogue=None):
        if catalogue is None:
            catalogue = definitions.Catalogue(
                DataGroupImporterCatalogue(),
                ModelImporterCatalogue(),
            )
        self.catalogue = catalogue
        self.zipfile = zipfile
        self.workdir = None
        self.meta = None
        self.logger = logging.getLogger(__name__)

    def find_workdir(self, startdir):
        """Return the workdir and the meta file location in the archive.

        The zip file can contain the META file at top level or in a nested
        directory. We find the META file and the directory containing it will
        be the working directory."""

        meta = [(path, os.path.join(path, 'META'))
                for path, _, files in os.walk(startdir) if 'META' in files]
        if len(meta) == 0:
            raise ImportError("Invalid export file '%s'.'META' file is missing." % self.zipfile)

        return meta[0]

    def extract_meta_info(self, meta_file):
        with open(meta_file) as f:
            self.meta = json.load(f)

    def create_importer(self, export_type, requested_import_type=None):
        self.file_export_type = definitions.ExportTypes.from_name(export_type)
        if requested_import_type is None:
            requested_import_type = self.file_export_type.code

        self.requested_type = definitions.ExportTypes.from_code(requested_import_type)
        if not (
                self.requested_type is self.file_export_type or self.requested_type in self.file_export_type.includes):
            raise ImportError(
                "Invalid import type '%s' requested for file '%s' with type '%s'." %
                (requested_import_type, self.zipfile, self.file_export_type.code))

        if self.requested_type in definitions.ExportTypes.registry_types:
            return RegistryImporter(self)
        if self.requested_type is definitions.ExportTypes.CDES:
            return GenericImporter(self)
        if self.requested_type is definitions.ExportTypes.REFDATA:
            return GenericImporter(self)
        raise ImportError("Unrecognized export type '%s'." % (self.requested_type.code))

    def do_import(
            self,
            import_type=None,
            verbose=False,
            indented_logs=True,
            simulate=False,
            force=False):
        if verbose:
            self.logger.setLevel(logging.DEBUG)
        self.child_logger = logger
        if indented_logs:
            self.child_logger = IndentedLogger(self.logger)
        self.simulate = simulate
        self.force = force

        with zipfile_contents(self.zipfile) as tmpdir:
            self.workdir, meta_file = self.find_workdir(tmpdir)
            self.extract_meta_info(meta_file)

            importer = self.create_importer(
                get_meta_value(
                    self.meta,
                    'type'),
                requested_import_type=import_type)
            importer.output_import_info()
            importer.do_import()

    def inspect(self):
        self.logger.setLevel(logging.DEBUG)
        with zipfile_contents(self.zipfile) as tmpdir:
            self.workdir, meta_file = self.find_workdir(tmpdir)
            self.extract_meta_info(meta_file)
            importer = self.create_importer(get_meta_value(self.meta, 'type'))
            importer.output_import_info()


class RegistryLevelChecks(DelegateMixin):

    def __init__(self, importer):
        DelegateMixin.__init__(self, delegate_to=importer)

    def check_registry_export_type_in_meta(self):
        export_type = get_meta_value(self.meta, 'type')
        if export_type not in definitions.ExportTypes.registry_types_names:
            raise ImportError("Invalid export type '%s' for registry import. Should be one of '%s'." % (
                export_type, ', '.join(definitions.ExportTypes.registry_types_names)))

    @allow_if_forced
    def check_registry_does_not_exist(self):
        if self.force:
            return
        if Registry.objects.filter(code=self.registry_code).exists():
            raise ImportError("Registry '%s' already exists." % self.registry_code)


class BaseImporter(DelegateMixin):

    def __init__(self, zipfile_importer):
        DelegateMixin.__init__(self, delegate_to=zipfile_importer)

    def maybe_filter_meta(self, meta):
        if self.file_export_type is self.requested_type:
            return meta
        else:
            return list(filter(definitions.META_FILTERS[self.requested_type], meta))

    @allow_if_forced
    def check_app_schema_versions_match(self):
        app_schema_version_different = self.diff_app_versions()
        if len(app_schema_version_different) > 0:
            raise ImportError(
                'Schema difference detected between your registry and the export file.'
                ' App(s) with different schema: %s' %
                ', '.join(app_schema_version_different))

    def reset_sql_sequences(self):
        meta = self.maybe_filter_meta(get_meta_value(self.meta, 'data_groups'))
        apps = sorted(
            reduce(
                lambda d,
                x: d.union(
                    x.get(
                        'app_versions',
                        {}).keys()),
                meta,
                set()))
        reset_sql_sequences(apps)

    def import_datagroups(self, meta):
        meta = self.maybe_filter_meta(meta)
        self.check_app_schema_versions_match()
        datagroup_importers = self.catalogue.datagroups
        for data_group_meta in meta:
            importer = datagroup_importers.get(data_group_meta['name'])(self.catalogue)
            options = {
                'logger': self.child_logger,
                'simulate': self.simulate,
                'force': self.force,
            }
            if hasattr(self, 'registry_code'):
                options['registry_code'] = self.registry_code
            importer.do_import(data_group_meta, self.workdir, **options)
        self.reset_sql_sequences()

    def output_import_info(self):
        logger = IndentedLogger(self.logger, indent_level=2)
        zipfile_type = definitions.ExportTypes.from_name(get_meta_value(self.meta, 'type'))
        logger.info('Zipfile type: %s (%s)', zipfile_type.name, zipfile_type.code)
        also_includes = zipfile_type.includes
        if also_includes:
            logger.info('(also includes import types: %s)' %
                        ', '.join("'%s' (%s)" % (t.name, t.code) for t in also_includes))

        app_schema_version_different = self.diff_app_versions()
        if len(app_schema_version_different) > 0:
            logger.warning(
                'WARNING: Schema difference detected between your registry and the export file.'
                'App(s): %s', ', '.join(app_schema_version_different))

        return logger

    def diff_app_versions(self):
        meta = self.maybe_filter_meta(get_meta_value(self.meta, 'data_groups'))
        app_versions = dict(
            reduce(
                lambda d,
                x: d + list(
                    x.get(
                        'app_versions',
                        {}).items()),
                meta,
                []))
        return [app for app in app_versions if app_versions[app] != app_schema_version(app)]


class RegistryImporter(BaseImporter):

    def __init__(self, zipfile_importer):
        BaseImporter.__init__(self, zipfile_importer)
        self.checks = RegistryLevelChecks(self)
        self.registry_code = None

    def do_import(self):
        self.checks.check_registry_export_type_in_meta()
        self.registry_code = get_meta_value(self.meta, 'registry.code')
        self.checks.check_registry_does_not_exist()

        with transaction.atomic():
            self.import_datagroups(get_meta_value(self.meta, 'data_groups'))

    def output_import_info(self):
        logger = BaseImporter.output_import_info(self)
        registry = get_meta_value(self.meta, 'registry')
        logger.info(
            'Registry: %s (%s v%s)',
            registry.get('name'),
            registry.get('code'),
            registry.get('version'))
        logger.info(' ' * len('Registry: ') + '%s', registry.get('description'))
        logger.info(
            'Exported at: %s',
            dateutil.parser.parse(
                get_meta_value(
                    self.meta,
                    'exported_at')))


META_FILTERS = {
    definitions.ExportTypes.CDES: lambda m: m['name'] == 'CDEs',
    definitions.ExportTypes.REFDATA: lambda m: m['name'] == 'Reference Data',
    definitions.ExportTypes.REGISTRY_DEF: lambda m: m['name'] != 'Registry Data',
}


class GenericImporter(BaseImporter):

    def do_import(self):
        with transaction.atomic():
            self.import_datagroups(get_meta_value(self.meta, 'data_groups'))
