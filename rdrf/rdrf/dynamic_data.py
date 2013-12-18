from django.core.files.uploadedfile import InMemoryUploadedFile
from pymongo import MongoClient
import gridfs
import logging
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

    def __init__(self, obj):
        self.obj = obj
        self.client = MongoClient()

    def __unicode__(self):
        return "Dynamic Data Wrapper for %s id=%s" % self.obj.__class__.__name__, self.obj.pk

    def _get_record(self):
        django_model = self.obj.__class__.__name__
        django_id = self.obj.pk
        return {"django_model": django_model,
                "django_id": django_id}

    def _get_collection(self, registry, collection_name):
        db = self.client[registry]
        collection = db[collection_name]
        return collection

    def _get_filestore(self, registry):
        db = self.client[registry]
        return gridfs.GridFS(db,collection=registry + ".files")


    def load_dynamic_data(self, registry, collection_name):
        """
        :param registry: e.g. sma or dmd
        :param collection_name: e.g. cde or hpo
        :return:
        """
        logger.debug("%s: loading data for %s %s" % (self, registry, collection_name))
        record = self._get_record()
        collection = self._get_collection(registry, collection_name)
        data = collection.find_one(record)
        self._munge_uploaded_file_data(registry, data)
        logger.debug("%s: dynamic data = %s" % (self, data))
        return data

    def _munge_uploaded_file_data(self, registry, data):
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
                            self.url = "/%s/uploads/%s" % (registry, str(self.gridfs_dict['gridfs_file_id']))

                        def __unicode__(self):
                            """
                            This is to satisfy Django's ClearableFileInputWidget which
                            uses django's force_text function
                            """
                            return self.gridfs_dict['file_name']

                    wrapper = FileUpload(registry, key, value)
                    data[key] = wrapper


        logger.debug("munged data = %s" % data)




    def _get_gridfs_filename(self, registry, data_record, cde_code, original_file_name):
        return "%s****%s****%s****%s****%s" % (registry, data_record["django_model"], data_record["django_id"], cde_code,original_file_name)

    def _store_file(self, registry, patient_record, cde_code, in_memory_file, dynamic_data):
        fs = self._get_filestore(registry)
        original_file_name = in_memory_file.name
        file_name = self._get_gridfs_filename(registry, patient_record, cde_code, original_file_name)
        gridfs_id = fs.put(in_memory_file.read(), filename=file_name)
        # _alter_ the dyamic data to store reference to gridfs + the original file name
        dynamic_data[cde_code] = {"gridfs_file_id" : gridfs_id, "file_name" : in_memory_file.name}
        logger.debug("UPLOADED FILE %s = %s into registry %s as %s ( dict = %s )" % (cde_code, original_file_name, registry, gridfs_id, dynamic_data[cde_code]))
        return gridfs_id

    def  _is_uploaded_file(self, code):
        from models import CommonDataElement
        cde = CommonDataElement.objects.get(code=code)
        if cde.datatype == 'file':
            return True
        #isinstance(value, InMemoryUploadedFile)

    def _update_any_files(self, record, registry, data):
        fs = self._get_filestore(registry)
        for key, value in data.items():
            if self._is_uploaded_file(key):
                logger.debug("uploaded file: %s" % key)
                if not value:
                    # we need to delete the file
                    continue

                file_wrapper = record[key]

                if not file_wrapper:
                    self._store_file(registry, record, key, value, data)
                else:
                    gridfs_file_dict = file_wrapper.gridfs_dict

                    if gridfs_file_dict is None:
                        self._store_file(registry, record, key, value, data)
                    else:
                        gridfs_file_id = gridfs_file_dict["gridfs_file_id"]
                        if fs.exists(gridfs_file_id):
                            fs.delete(gridfs_file_id)
                        self._store_file(registry, record, key, value, data)


    def save_dynamic_data(self, registry, collection_name, data):
        file_store = self._get_filestore(registry)
        logger.debug("data = %s" % data)
        self._convert_date_to_datetime(data)
        logger.debug("%s: save dynanmic data - registry = %s collection_name = %s data = %s" % (self, registry, collection_name, data))
        collection = self._get_collection(registry, collection_name)
        record = self.load_dynamic_data(registry, collection_name)
        if record:
            logger.debug("%s: updating existing mongo data record %s" % (self,record))
            mongo_id = record['_id']
            logger.debug("data before saving files = %s" % data)
            self._update_any_files(record, registry, data)
            logger.debug("data to update = %s" % data)
            collection.update({'_id': mongo_id}, {"$set": data }, upsert=False)
            logger.debug("%s: updated record %s OK" % (self,record))
        else:
            logger.debug("adding new mongo record")
            record = self._get_record()
            for code, value in data.items():
                if self._is_uploaded_file(code):
                    if isinstance(value, bool):
                        if not value:
                            # this is how django signals the file should be disassociated
                            # in our case we delete the file in mongo
                            from bson.objectid import ObjectId
                            file_id = record[code]["gridfs_file_id"]
                            file_store.delete(ObjectId(file_id))
                            del record[code]
                    else:
                        gridfs_file_id = self._store_file(registry, record, code, value, data)
                        record[code] = {"gridfs_file_id": gridfs_file_id, "file_name": value.name }
                else:
                    record[code] = value

            collection = self._get_collection(registry, collection_name)
            collection.insert(record)
            logger.debug("%s: inserted record %s OK" % (self,record))



    def _convert_date_to_datetime(self, data):
                """
                pymongo doesn't allow saving datetime.Date

                :param data: dictionary of CDE codes --> values
                :return:
                """
                import types
                from datetime import date
                from datetime import datetime

                for k in data:
                    value = data[k]
                    if type(value) is date:
                        data[k] = datetime(value.year, value.month, value.day)