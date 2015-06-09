from pymongo import MongoClient
from django.conf import settings
from rdrf.utils import mongo_db_name, mongo_key


class ProgressType(object):
    DIAGNOSIS = "diagnosis"
    GENETIC = "genetic"

class FormProgressCalculator(object):
    def __init__(self, registry_model):
        self.registry_model = registry_model
        self.client = MongoClient(settings.MONGOSERVER, settings.MONGOPORT)
        self.db_name = mongo_db_name(self.registry_model.code)
        self.db = self.client[self.db_name]
        self.cdes_collection = self.db["cdes"]

    def _get_mongo_data(self, patient_ids):
        query = {"django_model": "Patient", "django_id": {"$in": patient_ids}}
        return [doc for doc in self.cdes_collection.find(query)]

    def _progress_for_keys(self, data, mongo_keys):
        total = len(mongo_keys)
        have_non_empty_data = 0
        for mongo_key in mongo_keys:
            try:
                value = data[mongo_key]
                if value is not None:
                    have_non_empty_data += 1
            except KeyError:
                pass
        try:
            percentage = 100.00 * (float(have_non_empty_data)/float(len(mongo_keys)))
        except Exception:
            percentage = 0.00

        return have_non_empty_data, total, percentage

    def progress(self, patient_ids, progress_type=ProgressType.DIAGNOSIS):
        results = {}
        mongo_keys = self._get_mongo_keys(progress_type=progress_type)
        mongo_data = self._get_mongo_data(patient_ids)
        for patient_data in mongo_data:
            patient_id = patient_data["django_id"]
            results[patient_id] = self._progress_for_keys(patient_data, mongo_keys)[2]
        return results

    def _get_mongo_keys(self, progress_type=ProgressType.DIAGNOSIS):
        if progress_type == ProgressType.DIAGNOSIS:
            mongo_keys = [mongo_key(triple[0].name, triple[1].code, triple[2].code) for triple in
                          self.registry_model.diagnosis_progress_cde_triples]

        else:
            mongo_keys = [mongo_key(triple[0].name, triple[1].code, triple[2].code) for triple in
                          self.registry_model.genetic_progress_cde_triples]

        return mongo_keys






