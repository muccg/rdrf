from pymongo import MongoClient
import logging
logger = logging.getLogger("registry_log")

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
        logger.debug("%s: dynamic data = %s" % (self, data))
        return data

    def save_dynamic_data(self, registry, collection_name, data):
        self._convert_date_to_datetime(data)
        logger.debug("%s: save dyanmic data - registry = %s collection_name = %s data = %s" % (self, registry, collection_name, data))
        collection = self._get_collection(registry, collection_name)
        record = self.load_dynamic_data(registry, collection_name)
        if record:
            logger.debug("%s: updating existing mongo data record %s" % (self,record))
            mongo_id = record['_id']
            collection.update({'_id': mongo_id}, {"$set": data }, upsert=False)
            logger.debug("%s: updated record %s OK" % (self,record))
        else:
            logger.debug("adding new mongo record")
            record = self._get_record()
            for code, value in data.items():
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