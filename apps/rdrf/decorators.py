def has_dynamic_data(cls):
    """
    :param cls: the Registry Model class to decorate
    :return: The class with extra methods to get dynamic data from MongoDB
    """

    def _get_record(self):
        django_model = self.__class__.__name__
        django_id = self.pk
        return {"django_model": django_model,
                "django_id": django_id}

    def _get_collection(self, registry, collection_name):
        from pymongo import MongoClient
        client = MongoClient()
        db = client[registry]
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

    setattr(cls, '_get_record', _get_record)
    setattr(cls, '_get_collection', _get_collection)
    setattr(cls, 'load_dynamic_data', load_dynamic_data)
    setattr(cls, 'save_dynamic_data', save_dynamic_data)

    return cls














