from django.core.files.uploadedfile import InMemoryUploadedFile
from pymongo import MongoClient
import gridfs
import logging
from rdrf.utils import get_code
from bson.objectid import ObjectId

logger = logging.getLogger("registry_log")

class FileStore(object):
    def __init__(self,mongo_db):
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
    def __init__(self, obj, client=MongoClient(), filestore_class=gridfs.GridFS):
        self.testing = False # When set to True by integration tests, uses testing mongo database
        self.obj = obj
        self.django_id = obj.pk
        self.django_model = obj.__class__
        # We inject these to allow unit testing
        self.client = client
        self.file_store_class = filestore_class

        self.patient_record = None # holds reference to the complete data record for this object

    def __unicode__(self):
        return "Dynamic Data Wrapper for %s id=%s" % self.obj.__class__.__name__, self.obj.pk

    def _get_record_query(self):
        django_model = self.obj.__class__.__name__
        django_id = self.obj.pk
        return {"django_model": django_model,
                "django_id": django_id}

    def _get_collection(self, registry, collection_name):
        if not self.testing:
            db = self.client[registry]
        else:
            logger.debug("getting test db..")
            db = self.client["testing_" + registry]

        collection = db[collection_name]
        return collection

    def _get_filestore(self, registry):
        if not self.testing:
            db = self.client[registry]
        else:
            db = self.client["testing_" + registry]

        return self.file_store_class(db, collection=registry + ".files")


    def load_dynamic_data(self, registry, collection_name):
        """
        :param registry: e.g. sma or dmd
        :param collection_name: e.g. cde or hpo
        :return:
        """
        logger.debug("%s: loading data for %s %s" % (self, registry, collection_name))
        record_query = self._get_record_query()
        collection = self._get_collection(registry, collection_name)
        data = collection.find_one(record_query)
        self._wrap_gridfs_files_from_mongo(registry, data)
        logger.debug("%s: dynamic data = %s" % (self, data))
        return data

    def _wrap_gridfs_files_from_mongo(self, registry, data):
        """

        :param data: Dynamic data loaded from Mongo
        :return: --  nothing Munges the passed in dictionary

        """
        if data is None:
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

        logger.debug("wrapped gridfs data = %s" % data)




    def _get_gridfs_filename(self, registry, data_record, cde_code, original_file_name):
        return "%s****%s****%s****%s****%s" % (registry,self.django_model,self.django_id, cde_code,original_file_name)

    def _store_file_in_gridfs(self, registry, patient_record, cde_code, in_memory_file, dynamic_data):
        fs = self._get_filestore(registry)
        original_file_name = in_memory_file.name
        file_name = self._get_gridfs_filename(registry, patient_record, cde_code, original_file_name)
        gridfs_id = fs.put(in_memory_file.read(), filename=file_name)
        # _alter_ the dyamic data to store reference to gridfs + the original file name
        dynamic_data[cde_code] = {"gridfs_file_id" : gridfs_id, "file_name" : in_memory_file.name}
        logger.debug("UPLOADED FILE %s = %s into registry %s as %s ( dict = %s )" % (cde_code, original_file_name, registry, gridfs_id, dynamic_data[cde_code]))
        return gridfs_id

    def  _is_file_cde(self, code):
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
                DELETE_EXISTING = True
                logger.debug("uploaded file: %s" % key)
                if value is False:
                    logger.debug("User cleared %s - file will be deleted" % key)
                    # Django uses a "clear" checkbox value of False to indicate file should be removed
                    # we need to delete the file but not here
                    continue

                if value is None:
                    logger.debug("User did change file %s - existing_record will not be updated" % key)
                    logger.debug("existing_record = %s\nnew_data = %s" % (existing_record, new_data))
                    DELETE_EXISTING = False

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
                        if DELETE_EXISTING:
                            logger.debug("updated value is not None so we delete existing upload and update:")
                            if fs.exists(gridfs_file_id):
                                fs.delete(gridfs_file_id)
                                logger.debug("deleted existing file with id %s" % gridfs_file_id )
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
        if record:
            logger.debug("%s: updating existing mongo data record %s" % (self,record))
            mongo_id = record['_id']
            logger.debug("data before saving files = %s" % data)
            self._update_files_in_gridfs(record, registry, data)
            logger.debug("mongo data to update = %s" % data)
            collection.update({'_id': mongo_id}, {"$set": data }, upsert=False)
            logger.info("%s: updated record %s OK" % (self,record))
        else:
            logger.debug("adding new mongo record")
            record = self._get_record_query()

            record.update(data)
            self._set_in_memory_uploaded_files_to_none(record)
            self._update_files_in_gridfs(record, registry, data)
            logger.debug("about to insert mongo record: %s" % record)
            collection.insert(record)
            logger.info("%s: inserted record %s OK" % (self,record))

    def _convert_date_to_datetime(self, data):
        """
        pymongo doesn't allow saving datetime.Date

        :param data: dictionary of CDE codes --> values
        :return:
        """
        import types
        from datetime import date
        from datetime import datetime

        for k, value in data.items():
            if type(value) is date:
                data[k] = datetime(value.year, value.month, value.day)
            elif isinstance(value, list):
                # recurse on multisection data
                for e in value:
                    self._convert_date_to_datetime(e)


    def _set_in_memory_uploaded_files_to_none(self, data):

        keys_to_change = []
        for key, value in data.items():
            if isinstance(value, InMemoryUploadedFile):
                keys_to_change.append(key)
            elif isinstance(value, list):
                for item in value:
                    self._set_in_memory_uploaded_files_to_none(item)
        for key in keys_to_change:
            data[key] = None
