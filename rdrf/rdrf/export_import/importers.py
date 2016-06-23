from bson.json_util import loads
from functools import wraps
import logging
import os
from django.core import serializers
from django.apps import apps

from rdrf.mongo_client import construct_mongo_client
from rdrf.utils import mongo_db_name
from .utils import file_checksum, maybe_indent
from .exceptions import ImportError


logger = logging.getLogger(__name__)


def allow_if_forced(checkfn):
    @wraps(checkfn)
    def wrapper(self, *args, **kwargs):
        try:
            return checkfn(self, *args, **kwargs)
        except ImportError as exc:
            if self.force:
                self.logger.warn('FORCED THROUGH, despite WARNING: %s', exc)
            else:
                raise

    return wrapper


class DataGroupImporter(object):
    def __init__(self, catalogue):
        self.catalogue = catalogue
        self.logger = logger

    def import_datagroups(self, datagroups_meta, workdir, **options):
        if len(datagroups_meta) > 0:
            self.logger.debug('Importing %d datagroups', len(datagroups_meta))
        for datagroup_meta in datagroups_meta:
            importer = self.catalogue.datagroups.get(get_meta_value(datagroup_meta, 'name'))(self.catalogue)
            importer.do_import(datagroup_meta, workdir, **options)

    def import_models(self, models_meta, workdir, **options):
        for model_meta in models_meta:
            importer = self.catalogue.models.get(get_meta_value(model_meta, 'model_name'))()
            importer.do_import(model_meta, workdir, **options)

    def import_collections(self, collections_meta, workdir, **options):
        for collection_meta in collections_meta:
            importer = self.catalogue.mongo_collections.get(get_meta_value(collection_meta, 'collection_name'))()
            importer.do_import(collection_meta, workdir, **options)

    def do_import(self, datagroup_meta, parent_workdir, registry_code=None, logger=None, simulate=False, force=False):
        if logger is not None:
            self.logger = logger
        self.child_logger = maybe_indent(self.logger)

        self.logger.debug("Importing data group '%s'", get_meta_value(datagroup_meta, 'name'))

        datagroup_dir = get_meta_value(datagroup_meta, 'dir_name')
        workdir = os.path.join(parent_workdir, datagroup_dir)

        options = {
            'logger': self.child_logger,
            'simulate': simulate,
            'force': force,
        }
        if registry_code is not None:
            options['registry_code'] = registry_code

        self.import_datagroups(datagroup_meta.get('data_groups', []), workdir, **options)
        self.import_models(datagroup_meta.get('models', []), workdir, **options)
        self.import_collections(datagroup_meta.get('collections', []), workdir, **options)


class ModelImporter(object):
    @allow_if_forced
    def check_checksum(self, file_name, expected_checksum):
        actual_checksum = file_checksum(file_name)
        if actual_checksum != expected_checksum:
            raise ImportError("Invalid checksum on file '%s'. Actual: '%s', expected: '%s'" % (file_name, actual_checksum, expected_checksum))

    @allow_if_forced
    def check_object_count(self, model_name, expected, actual):
        if actual != expected:
            raise ImportError("Invalid object_count for model '%s'. Actual: %d, expected: %d" % (model_name, actual, expected))

    @allow_if_forced
    def check_no_data_in_table(self, model_name):
        model = apps.get_model(model_name)
        if model.objects.count() > 0:
            raise ImportError("Refusing to import over existing data for model '%s'." % model_name)

    def do_import(self, model_meta, workdir, logger=None, simulate=False, force=False, **kwargs):
        self.logger = logger
        self.child_logger = maybe_indent(self.logger)
        self.force = force

        model_name = get_meta_value(model_meta, 'model_name')
        file_name = os.path.join(workdir, get_meta_value(model_meta, 'file_name'))
        checksum = get_meta_value(model_meta, 'md5_checksum')
        object_count = get_meta_value(model_meta ,'object_count')

        self.logger.debug("Importing model '%s'", model_name)
        self.check_checksum(file_name, checksum)

        self.check_no_data_in_table(model_name)

        with open(file_name) as f:
            if simulate:
                # We can't deserialize objects when simulating, because FK
                # references to models we only simulated to save will fail.
                # We could model.save() all models in a transaction that we
                # we roll back, but that feels too dangerous
                _ = f.read()
                self.child_logger.debug('Would import %d models', object_count)
                return

            actual_object_count = 0
            for model in serializers.deserialize('json', f.read()):
                model.save()
                actual_object_count += 1
            self.check_object_count(model_name, object_count, actual_object_count)
            self.child_logger.debug('Imported %d models', actual_object_count)


class MongoCollectionImporter(object):
    @allow_if_forced
    def check_no_data_in_collection(self, collection):
        if collection.count() > 0:
            raise ImportError("Refusing to import over existing data for collection '%s'." % collection.name)

    def do_import(self, collection_meta, workdir, registry_code=None, logger=None, simulate=False, force=False, **kwargs):
        self.logger = logger
        self.child_logger = maybe_indent(self.logger)
        self.force = force

        collection_name = get_meta_value(collection_meta, 'collection_name')
        file_name = os.path.join(workdir, get_meta_value(collection_meta, 'file_name'))

        self.logger.debug("Importing collection '%s'", collection_name)

        client = construct_mongo_client()
        db = client[mongo_db_name(registry_code)]
        if collection_name not in db.collection_names():
            self.logger.warning("Collection '%s' doesn't exist for registry '%s'."
                % (collection_name, registry_code))
        collection = db[collection_name]

        self.check_no_data_in_collection(collection)

        with open(file_name) as f:
            docs = loads(f.read())
            if not simulate:
                collection.insert(docs)
            self.child_logger.debug('Inserted %d documents', len(docs))


def get_meta_value(meta, key, path=None):
    if '.' not in key:
        if key not in meta:
            raise ImportError("Invalid META file. Required entry '%s' is missing."
                    % (key if path is None else '.'.join((path, key))))
        return meta[key]

    first_key, rest = key.split('.', 1)
    next_meta = get_meta_value(meta, first_key, path)
    next_path = first_key if path is None else '.'.join((path, first_key))
    return get_meta_value(next_meta, rest, next_path)
