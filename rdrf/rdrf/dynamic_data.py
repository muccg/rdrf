from django.core.files.uploadedfile import InMemoryUploadedFile
from pymongo import MongoClient
import gridfs
import logging
from rdrf.utils import get_code

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
                            from django.core.urlresolvers import reverse
                            self.url = reverse("file_upload", args=[registry, str(self.gridfs_dict['gridfs_file_id'])])
                            #self.url = "/%s/uploads/%s" % (registry, str(self.gridfs_dict['gridfs_file_id']))

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

    def _update_any_files(self, record, registry, data):
        fs = self._get_filestore(registry)
        for key, value in data.items():
            if self._is_uploaded_file(get_code(key)):
                DELETE_EXISTING = True
                logger.debug("uploaded file: %s" % key)
                if value is False:
                    logger.debug("User cleared %s - file will be deleted" % key)
                    # Django uses a "clear" checkbox value of False to indicate file should be removed
                    # we need to delete the file but not here
                    continue

                if value is None:
                    logger.debug("User did change file %s - record will not be updated" % key)
                    # If no file is chosen, value is None
                    # We don't want to update anything
                    logger.debug("record = %s\ndata = %s" % (record, data))
                    DELETE_EXISTING = False

                if key in record:
                    file_wrapper = record[key]
                else:
                    file_wrapper = None

                logger.debug("File wrapper = %s" % file_wrapper)

                if not file_wrapper:
                    if value is not None:
                        logger.debug("storing file for %s data = %s" % (key, data))
                        self._store_file(registry, record, key, value, data)
                    else:
                        logger.debug("did not update file as value is None")
                else:
                    gridfs_file_dict = file_wrapper.gridfs_dict
                    logger.debug("existing gridfs dict = %s" % gridfs_file_dict)

                    if gridfs_file_dict is None:
                        if value is not None:
                            logger.debug("storing file with value %s" % value)
                            self._store_file(registry, record, key, value, data)
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
                                logger.debug("file id %s in record didn't exist?" % gridfs_file_id)
                            if value is not None:
                                logger.debug("updating %s -> %s" % (key, value))
                                self._store_file(registry, record, key, value, data)
                        else:
                            # don't change anything on update ...
                            data[key] = gridfs_file_dict


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
            for delimited_key, value in data.items():
                if self._is_uploaded_file(get_code(delimited_key)):
                    if isinstance(value, bool):
                        if not value:
                            # this is how django signals the file should be disassociated
                            # in our case we delete the file in mongo
                            from bson.objectid import ObjectId
                            file_id = record[delimited_key]["gridfs_file_id"]
                            file_store.delete(ObjectId(file_id))
                            del record[delimited_key]
                    elif value is None:
                        # The file hasn't changed
                        pass
                    else:
                        gridfs_file_id = self._store_file(registry, record, delimited_key, value, data)
                        record[delimited_key] = {"gridfs_file_id": gridfs_file_id, "file_name": value.name }
                else:
                    record[delimited_key] = value

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