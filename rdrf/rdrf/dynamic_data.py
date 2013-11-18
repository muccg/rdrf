from pymongo import MongoClient

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
        record = self._get_record()
        collection = self._get_collection(registry, collection_name)
        return collection.find_one(record)

    def save_dynamic_data(self, registry, collection_name, data):
        collection = self._get_collection(registry, collection_name)
        record = self.load_dynamic_data(registry, collection_name)
        if record:
            mongo_id = record['_id']
            collection.update({'_id': mongo_id}, {"$set": data}, upsert=False)
        else:
            record = self._get_record()
            for code, value in data.items():
                record[code] = value

            collection = self._get_collection(registry, collection_name)
            collection.insert(record)