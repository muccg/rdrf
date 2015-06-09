from pymongo import MongoClient
from django.conf import settings
from rdrf.utils import mongo_db_name, mongo_key, de_camelcase
from rdrf.models import RegistryForm
import logging
import datetime

logger = logging.getLogger("registry_log")


class ProgressType(object):
    DIAGNOSIS = "diagnosis"
    GENETIC = "genetic"


class ProgressCalculationError(Exception):
    pass


class FormProgressCalculator(object):


    def __init__(self, registry_model, user):
        self.user = user
        self.registry_model = registry_model

        self.viewable_forms = [f for f in RegistryForm.objects.filter(registry=self.registry_model).order_by('position')
                 if self._not_generated_form(f) and self.user.can_view(f)]

        # List of (form_model, section_model, cde_model) triples
        self.diagnosis_triples = self.registry_model.diagnosis_progress_cde_triples
        self.genetic_triples = self.registry_model.genetic_progress_cde_triples
        self.diagnosis_forms = self._get_diagnosis_forms()
        self.genetic_forms = self._get_genetic_forms()
        self.patient_ids = []

        self.client = MongoClient(settings.MONGOSERVER, settings.MONGOPORT)
        self.db_name = mongo_db_name(self.registry_model.code)
        self.db = self.client[self.db_name]
        self.cdes_collection = self.db["cdes"]
        self.mongo_data = []
        self.form_currency = {}  # {patient_id : {form name : bool}}



    def _get_genetic_keys(self):
        keys = []
        for form_model in self.genetic_forms:
            for section_model in form_model.section_models:
                for cde_model in section_model.cde_models:
                    key = mongo_key(form_model.name, section_model.code,cde_model.code)
                    keys.append(key)
        return keys

    def _get_diagnosis_forms(self):
        return [form_model for form_model in
                self.registry_model.forms if "genetic" not in form_model.name.lower()]

    def _get_genetic_forms(self):
        return [form_model for form_model in
                self.registry_model.forms if "genetic" in form_model.name.lower()]

    def _get_mongo_data(self, patient_ids):
        self.patient_ids = patient_ids
        query = {"django_model": "Patient", "django_id": {"$in": patient_ids}}
        return [doc for doc in self.cdes_collection.find(query)]

    def _progress_for_keys(self, patient_mongo_data, mongo_keys):
        total = len(mongo_keys)
        have_non_empty_data = 0
        for mongo_key in mongo_keys:
            try:
                value = patient_mongo_data[mongo_key]
                if value is not None:
                    have_non_empty_data += 1
            except KeyError:
                pass
        try:
            percentage = 100.00 * (float(have_non_empty_data)/float(len(mongo_keys)))
        except Exception:
            percentage = 0.00

        return have_non_empty_data, total, percentage

    def _get_mongo_keys_for_triples(self, triples):
        return [mongo_key(triple[0].name, triple[1].code, triple[2].code) for triple in triples]

    def load_data(self, patient_ids):
        self.mongo_data = self._get_mongo_data(patient_ids)

    def _progress(self, progress_type=ProgressType.DIAGNOSIS):

        results = {}

        if progress_type == ProgressType.DIAGNOSIS:
            triples = self.diagnosis_triples
        else:
            triples = self.genetic_triples

        mongo_keys = self._get_mongo_keys_for_triples(triples)

        for patient_data in self.mongo_data:
            patient_id = patient_data["django_id"]
            results[patient_id] = self._progress_for_keys(patient_data, mongo_keys)[2]
            logger.debug("diagnosis progress for patient %s = %s" % (patient_id, results[patient_id]))

        return results

    def diagnosis_progress(self):
        return self._progress()

    def _has_data(self, patient_data, cde_key):
        try:
            value = patient_data[cde_key]
            if value is not None:
                return True
            else:
                return False
        except KeyError:
            return False

    def has_genetic_data(self):
        keys = self._get_genetic_keys()
        results = {}
        for patient_data in self.mongo_data:
            results[patient_data["django_id"]] = False
            for key in keys:
                if self._has_data(patient_data, key):
                    results[patient_data["django_id"]] = True
                    break
        return results

    def genetic_progress(self):
        return self._progress(progress_type=ProgressType.GENETIC)

    def diagnosis_currency(self, num_days=365):
        results = {}
        for patient_data in self.mongo_data:
            results[patient_data["django_id"]] = self.data_currency_one_patient(patient_data,
                                                                                self.diagnosis_forms,
                                                                                num_days)
        return results

    def data_currency_one_patient(self, patient_data, form_models, days=365):
        time_window_start = datetime.datetime.now() - datetime.timedelta(days=days)
        for form_model in form_models:
            form_timestamp = self._get_form_timestamp(patient_data, form_model)
            if form_timestamp and form_timestamp >= time_window_start:
                    return True

        return False

    def _get_form_timestamp(self, patient_data, form_model=None):
        try:
            if form_model is None:
                return patient_data["timestamp"]
            else:
                key_name = "%s_timestamp" % form_model.name
                return patient_data[key_name]
        except KeyError:
            return None

    def _not_generated_form(self, form_model):
        return not form_model.name.startswith(self.registry_model.generated_questionnaire_name)

    def data_modules(self, patient_data):
        user = self.user
        registry_code = self.registry_model.code

        def nice_name(name):
            try:
                return de_camelcase(name)
            except:
                return name

        content = ''

        if not forms:
            content = "No modules available"

        for form in self.viewable_forms:
            if form.is_questionnaire:
                continue
            is_current = patient_model.form_currency(form)
            flag = "images/%s.png" % ("tick" if is_current else "cross")

            url = reverse('registry_form', args=(registry_model.code, form.id, patient_model.id))
            link = "<a href=%s>%s</a>" % (url, nice_name(form.name))
            label = nice_name(form.name)

            to_form = link
            if user.is_working_group_staff:
                to_form = label

            if form.has_progress_indicator:
                content += "<img src=%s> <strong>%d%%</strong> %s</br>" % (static(flag),
                                                                           patient_model.form_progress(form)[1],
                                                                           to_form)
            else:
                content += "<img src=%s> %s</br>" % (static(flag), to_form)

        return "<button type='button' class='btn btn-info btn-small' data-toggle='popover' data-content='%s' id='data-modules-btn'>Show Modules</button>" % content
