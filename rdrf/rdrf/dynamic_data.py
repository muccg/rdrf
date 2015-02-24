from django.core.files.uploadedfile import InMemoryUploadedFile
from pymongo import MongoClient
import gridfs
import logging
from rdrf.utils import get_code, mongo_db_name
from bson.objectid import ObjectId
from django.conf import settings
from utils import mongo_db_name
import datetime

logger = logging.getLogger("registry_log")


class FileStore(object):

    def __init__(self, mongo_db):
        self.fs = gridfs.GridFS(mongo_db)


class DynamicDataWrapper(object):

    """
    Utility class to save and load dynamic data for a Django model object
    Usage:
    E.G. wrapper = DynamicDataWrapper(patient)
    data = wrapper.load_dynamic_data("sma", "cdes)
    ... modify data to new_data
    wrapper.save_dynamic_data("sma","cdes", new_data)

    """
    REGISTRY_SPECIFIC_PATIENT_DATA_COLLECTION = "registry_specific_patient_data"

    def __init__(self, obj, client=MongoClient(settings.MONGOSERVER, settings.MONGOPORT), filestore_class=gridfs.GridFS):
        self.testing = False  # When set to True by integration tests, uses testing mongo database
        self.obj = obj
        self.django_id = obj.pk
        self.django_model = obj.__class__
        # We inject these to allow unit testing
        self.client = client
        self.file_store_class = filestore_class

        self.patient_record = None  # holds reference to the complete data record for this object

    def __unicode__(self):
        return "Dynamic Data Wrapper for %s id=%s" % self.obj.__class__.__name__, self.obj.pk

    def _get_record_query(self):
        django_model = self.obj.__class__.__name__
        django_id = self.obj.pk
        return {"django_model": django_model,
                "django_id": django_id}

    def _get_collection(self, registry, collection_name):
        if not self.testing:
            db = self.client[mongo_db_name(registry)]
        else:
            db = self.client["testing_" + registry]

        collection = db[collection_name]
        return collection

    def _get_filestore(self, registry):
        if not self.testing:
            db = self.client[mongo_db_name(registry)]
        else:
            db = self.client["testing_" + registry]

        return self.file_store_class(db, collection=registry + ".files")

    def load_dynamic_data(self, registry, collection_name):
        """
        :param registry: e.g. sma or dmd
        :param collection_name: e.g. cde or hpo
        :return:
        """
        record_query = self._get_record_query()
        collection = self._get_collection(registry, collection_name)
        data = collection.find_one(record_query)
        self._wrap_gridfs_files_from_mongo(registry, data)
        return data

    def load_registry_specific_data(self):
        data = {}
        record_query = self._get_record_query()
        logger.debug("record_query = %s" % record_query)
        for reg_code in self._get_registry_codes():
            logger.debug("checking for reg specific fields in registry %s" % reg_code)
            collection = self._get_collection(reg_code, self.REGISTRY_SPECIFIC_PATIENT_DATA_COLLECTION)
            registry_data = collection.find_one(record_query)
            logger.debug("registry_data = %s" % registry_data)
            if registry_data:
                for k in ['django_id', '_id', 'django_model']:
                    del registry_data[k]
                data[reg_code] = registry_data

        logger.debug("registry_specific_data  = %s" % data)
        return data

    def _get_registry_codes(self):
        reg_codes = self.client.database_names()
        logger.debug("reg_codes = %s" % reg_codes)
        return reg_codes

    def save_registry_specific_data(self, data):
        logger.debug("saving registry specific mongo data: %s" % data)
        for reg_code in data:
            logger.debug("saving data into %s db" % reg_code)
            registry_data = data[reg_code]
            logger.debug("data to save for %s = %s" % (reg_code, registry_data))
            collection = self._get_collection(reg_code, "registry_specific_patient_data")
            logger.debug("collection = %s" % collection)
            query = self._get_record_query()
            record = collection.find_one(query)
            if record:
                logger.debug("found record: %s" % record)
                mongo_id = record['_id']
                logger.debug("mongo id = %s" % mongo_id)
                collection.update({'_id': mongo_id}, {"$set": registry_data}, upsert=False)
                logger.debug("updated collection OK")
            else:
                logger.debug("record not found - inserting new record ...")
                record = self._get_record_query()
                record.update(registry_data)
                logger.debug("about tpo insert record %s into collection %s for registry %s" %
                             (record, collection, reg_code))
                collection.insert(record)
                logger.debug("inserted record OK")

    def _wrap_gridfs_files_from_mongo(self, registry, data):
        """

        :param data: Dynamic data loaded from Mongo
        :return: --  nothing Munges the passed in dictionary

        """
        if data is None:
            return
        if isinstance(data, unicode):
            return
        from django.conf import settings
        replacements = {}
        for key, value in data.items():
            if isinstance(value, dict):
                if "gridfs_file_id" in value:
                    class FileUpload(object):

                        def __init__(self, registry, cde_code, gridfs_dict):
                            self.cde_code = cde_code
                            self.gridfs_dict = gridfs_dict
                            from django.core.urlresolvers import reverse
                            self.url = reverse("file_upload", args=[registry, str(self.gridfs_dict['gridfs_file_id'])])

                        def __unicode__(self):
                            """
                            This is to satisfy Django's ClearableFileInputWidget which
                            uses django's force_text function
                            """
                            return self.gridfs_dict['file_name']

                    wrapper = FileUpload(registry, key, value)
                    data[key] = wrapper

            elif isinstance(value, list):
                # section data
                for section_dict in value:
                    self._wrap_gridfs_files_from_mongo(registry, section_dict)

    def _get_gridfs_filename(self, registry, data_record, cde_code, original_file_name):
        return "%s****%s****%s****%s****%s" % (registry, self.django_model, self.django_id, cde_code, original_file_name)

    def _store_file_in_gridfs(self, registry, patient_record, cde_code, in_memory_file, dynamic_data):
        fs = self._get_filestore(registry)
        original_file_name = in_memory_file.name
        file_name = self._get_gridfs_filename(registry, patient_record, cde_code, original_file_name)
        gridfs_id = fs.put(in_memory_file.read(), filename=file_name)
        # _alter_ the dyamic data to store reference to gridfs + the original file name
        dynamic_data[cde_code] = {"gridfs_file_id": gridfs_id, "file_name": in_memory_file.name}
        logger.debug("UPLOADED FILE %s = %s into registry %s as %s ( dict = %s )" %
                     (cde_code, original_file_name, registry, gridfs_id, dynamic_data[cde_code]))
        return gridfs_id

    def _is_file_cde(self, code):
        from models import CommonDataElement
        try:
            cde = CommonDataElement.objects.get(code=code)
            if cde.datatype == 'file':
                logger.debug("CDE %s is a file!" % cde.code)
                return True
            else:
                logger.debug("CDE %s is not a file" % cde.code)
        except Exception, ex:
            # section forms have codes which are not CDEs
            logger.debug("Error checking CDE code %s for being a file: %s" % (code, ex))
            return False

    def _is_section_code(self, code):
        # Supplied code will be non-delimited
        from models import Section
        try:
            section = Section.objects.get(code=code)
            return True
        except:
            pass
        return False

    def _update_files_in_gridfs(self, existing_record, registry, new_data):
        fs = self._get_filestore(registry)
        for key, value in new_data.items():
            if self._is_file_cde(get_code(key)):
                logger.debug("updating file reference for cde %s" % key)
                delete_existing = True
                logger.debug("uploaded file: %s" % key)
                if value is False:
                    logger.debug("User cleared %s - file will be deleted" % key)
                    # Django uses a "clear" checkbox value of False to indicate file should be removed
                    # we need to delete the file but not here
                    continue

                if value is None:
                    logger.debug("User did change file %s - existing_record will not be updated" % key)
                    logger.debug("existing_record = %s\nnew_data = %s" % (existing_record, new_data))
                    delete_existing = False

                if key in existing_record:
                    file_wrapper = existing_record[key]
                else:
                    file_wrapper = None

                logger.debug("File wrapper = %s" % file_wrapper)

                if not file_wrapper:
                    if value is not None:
                        logger.debug("storing file for cde %s value = %s" % (key, value))
                        self._store_file_in_gridfs(registry, existing_record, key, value, new_data)
                    else:
                        logger.debug("did not update file as value is None")
                else:
                    gridfs_file_dict = file_wrapper.gridfs_dict
                    logger.debug("existing gridfs dict = %s" % gridfs_file_dict)

                    if gridfs_file_dict is None:
                        if value is not None:
                            logger.debug("storing file with value %s" % value)
                            self._store_file_in_gridfs(registry, existing_record, key, value, new_data)
                    else:
                        logger.debug("checking file id on existing gridfs dict")
                        gridfs_file_id = gridfs_file_dict["gridfs_file_id"]
                        logger.debug("existing file id = %s" % gridfs_file_id)
                        if delete_existing:
                            logger.debug("updated value is not None so we delete existing upload and update:")
                            if fs.exists(gridfs_file_id):
                                fs.delete(gridfs_file_id)
                                logger.debug("deleted existing file with id %s" % gridfs_file_id)
                            else:
                                logger.debug("file id %s in existing_record didn't exist?" % gridfs_file_id)
                            if value is not None:
                                logger.debug("updating %s -> %s" % (key, value))
                                self._store_file_in_gridfs(registry, existing_record, key, value, new_data)
                        else:
                            # don't change anything on update ...
                            new_data[key] = gridfs_file_dict

            elif self._is_section_code(key):
                logger.debug("checking in section %s for files" % key)
                # value is a list of section field data dictionaries
                if key not in existing_record:
                    existing_record[key] = [{}] * len(value)
                elif len(existing_record[key]) < len(value):
                    num_extra_dicts = len(value) - len(existing_record[key])
                    existing_record[key].extend([{}] * num_extra_dicts)

                for i, section_data_dict in enumerate(value):
                    existing_section_dict = existing_record[key][i]
                    self._update_files_in_gridfs(existing_section_dict, registry, section_data_dict)

    def save_dynamic_data(self, registry, collection_name, data):
        file_store = self._get_filestore(registry)
        self._convert_date_to_datetime(data)
        collection = self._get_collection(registry, collection_name)
        record = self.load_dynamic_data(registry, collection_name)
        data["timestamp"] = datetime.datetime.now()
        if record:
            logger.debug("%s: updating existing mongo data record %s" % (self, record))
            mongo_id = record['_id']
            logger.debug("data before saving files = %s" % data)
            self._update_files_in_gridfs(record, registry, data)
            logger.debug("mongo data to update = %s" % data)
            collection.update({'_id': mongo_id}, {"$set": data}, upsert=False)
            logger.info("%s: updated record %s OK" % (self, record))
        else:
            logger.debug("adding new mongo record")
            record = self._get_record_query()

            record.update(data)
            self._set_in_memory_uploaded_files_to_none(record)
            self._update_files_in_gridfs(record, registry, data)
            logger.debug("about to insert mongo record: %s" % record)
            collection.insert(record)
            logger.info("%s: inserted record %s OK" % (self, record))

    def _save_longitudinal_snapshot(self, registry, record):
        try:
            from datetime import datetime
            timestamp = str(datetime.now())
            patient_id = record['django_id']
            history = self._get_collection(registry, "history")
            h = history.find_one({"_id": patient_id})
            if h is None:
                history.insert({"_id": patient_id, "snapshots": []})
            history.update({"_id": patient_id}, {"$push": {"snapshots": {"timestamp": timestamp, "record": record}}})
        except Exception, ex:
            logger.error("Couldn't add to history for patient %s: %s" % (patient_id, ex))

    def save_snapshot(self, registry_code, collection_name):
        try:
            record = self.load_dynamic_data(registry_code, collection_name)
            self._save_longitudinal_snapshot(registry_code, record)
        except Exception, ex:
            logger.error("Error saving longitudinal snapshot: %s" % ex)

    def _convert_date_to_datetime(self, data):
        """
        pymongo doesn't allow saving datetime.Date

        :param data: dictionary of CDE codes --> values
        :return:
        """
        import types
        from datetime import date
        from datetime import datetime

        if isinstance(data, unicode):
            return

        if isinstance(data, list):
            for x in data:
                self._convert_date_to_datetime(x)

        for k, value in data.items():
            if type(value) is date:
                data[k] = datetime(value.year, value.month, value.day)
            elif isinstance(value, list):
                # recurse on multisection data
                for e in value:
                    self._convert_date_to_datetime(e)

    def _set_in_memory_uploaded_files_to_none(self, data):
        if not isinstance(data, dict):
            # TODO find a better way! this test added to fix RDR-634
            # The items in a multiple allowed select widget were being passed in here
            # ( values in the list are not dicts so the recursive call failed below)
            return
        keys_to_change = []
        for key, value in data.items():
            if isinstance(value, InMemoryUploadedFile):
                keys_to_change.append(key)
            elif isinstance(value, list):
                for item in value:
                    self._set_in_memory_uploaded_files_to_none(item)
        for key in keys_to_change:
            data[key] = None

    def delete_patient_data(self, registry_model, patient_model):
        cdes = self._get_collection(registry_model, "cdes")
        cdes.remove({"django_id": patient_model.pk, "django_model": "Patient"})

    def get_cde(self, registry, section, cde_code):
        if not self.testing:
            db = self.client[mongo_db_name(registry)]
        else:
            db = self.client["testing_" + registry]

        collection = db["cdes"]
        cde_mongo_key = "%s____%s____%s" % (registry.upper(), section, cde_code)
        cde_record = collection.find_one(self._get_record_query(), {cde_mongo_key: True})
        cde_value = self._get_value_from_cde_record(cde_mongo_key, cde_record)

        return cde_value

    def _get_value_from_cde_record(self, cde_mongo_key, cde_record):
        try:
            return cde_record[cde_mongo_key]
        except KeyError:
            return None

    def get_form_timestamp(self, registry_form):
        if not self.testing:
            db = self.client[mongo_db_name(registry_form.registry.code)]
        else:
            db = self.client["testing_" + registry_form.registry.code]

        collection = db["cdes"]
        form_timestamp = collection.find_one(self._get_record_query(), {"timestamp": True})

        return form_timestamp
