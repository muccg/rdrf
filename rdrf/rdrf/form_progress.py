from pymongo import MongoClient
from django.conf import settings
from django.core.urlresolvers import reverse
from django.templatetags.static import static
from rdrf.utils import mongo_db_name, mongo_key, de_camelcase
from rdrf.models import RegistryForm
from registry.patients.models import Patient

import logging
import datetime

logger = logging.getLogger("registry_log")


class ProgressType(object):
    DIAGNOSIS = "diagnosis"
    GENETIC = "genetic"


class ProgressCalculationError(Exception):
    pass


def nice_name(name):
    try:
        return de_camelcase(name)
    except:
        return name


class FormProgressCalculator(object):

    def __init__(self, registry_model, user, patient_resource):
        self.user = user
        self.registry_model = registry_model
        self.patient_resource = patient_resource

        self.viewable_forms = [f for f in RegistryForm.objects.filter(registry=self.registry_model).order_by(
            'position') if self._not_generated_form(f) and self.user.can_view(f)]

        # List of (form_model, section_model, cde_model) triples
        self.diagnosis_triples = self.registry_model.diagnosis_progress_cde_triples
        logger.debug("xx diagnosis triples = %s" % self.diagnosis_triples)
        self.genetic_triples = self.registry_model.genetic_progress_cde_triples
        self.diagnosis_forms = self._get_diagnosis_forms()
        logger.debug("xx diagnosis forms = %s" % self.diagnosis_forms)
        self.genetic_forms = self._get_genetic_forms()
        logger.debug("xx genetic forms = %s" % self.genetic_forms)
        self.patient_ids = []
        # do this once to save time
        self.completion_keys_by_form = self._get_completion_keys_by_form()

        self.client = MongoClient(settings.MONGOSERVER, settings.MONGOPORT)
        self.db_name = mongo_db_name(self.registry_model.code)
        self.db = self.client[self.db_name]
        self.cdes_collection = self.db["cdes"]
        self.mongo_data = []
        self.form_currency = {}  # {patient_id : {form name : bool}}
        self.data_map = {}
        self.patient_ids_not_in_mongo = []

    def _get_completion_keys_by_form(self):
        key_map = {}
        for form_model in self.registry_model.forms:
            key_map[form_model.name] = []
            completion_codes = [
                cde_model.code for cde_model in form_model.complete_form_cdes.all()]
            for section_model in form_model.section_models:
                for cde_model in section_model.cde_models:
                    if cde_model.code in completion_codes:
                        if not section_model.allow_multiple:
                            key_map[form_model.name].append((mongo_key(form_model.name,
                                                                       section_model.code,
                                                                       cde_model.code),
                                                             None))
                        else:
                            key_map[form_model.name].append((mongo_key(form_model.name,
                                                                       section_model.code,
                                                                       cde_model.code),
                                                             section_model.code))
        return key_map

    def _get_genetic_keys(self):
        keys = []
        for form_model in self.genetic_forms:
            for section_model in form_model.section_models:
                for cde_model in section_model.cde_models:
                    key = mongo_key(form_model.name, section_model.code, cde_model.code)
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

    def _get_value_from_patient_mongo_data(self, patient_data, key):
        try:
            form_name, section_code, cde_code = key.split("____")
        except Exception:
            return
        for form_dict in patient_data["forms"]:
            if form_dict["name"] == form_name:
                for section_dict in form_dict["sections"]:
                    if section_dict["code"] == section_code:
                        if not section_dict["allow_multiple"]:
                            for cde_dict in section_dict["cdes"]:
                                if cde_dict["code"] == cde_code:
                                    return cde_dict["value"]
                        else:
                            # for progress we just need
                            for item in section_dict["cdes"]:
                                for cde_dict in item:
                                    if cde_dict["code"] == cde_code:
                                        if cde_dict["value"] is not None:
                                            return cde_dict["value"]

    def _progress_for_keys(self, patient_mongo_data, mongo_keys):
        total = len(mongo_keys)
        have_non_empty_data = 0
        for key in mongo_keys:
            try:
                value = self._get_value_from_patient_mongo_data(patient_mongo_data, key)
                if value:
                    have_non_empty_data += 1
            except KeyError:
                pass
        try:
            percentage = int(100.00 * (float(have_non_empty_data) / float(len(mongo_keys))))
        except Exception:
            percentage = 0

        return have_non_empty_data, total, percentage

    def _get_mongo_keys_for_triples(self, triples):
        return [mongo_key(triple[0].name, triple[1].code, triple[2].code) for triple in triples]

    def load_data(self, patient_ids):
        self.mongo_data = self._get_mongo_data(patient_ids)
        self.patient_ids_not_in_mongo = set(
            self.patient_ids) - set([mongo_record["django_id"] for mongo_record in self.mongo_data])

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
            logger.debug("diagnosis progress for patient %s = %s" %
                         (patient_id, results[patient_id]))

        for patient_id in self.patient_ids_not_in_mongo:
            results[patient_id] = 0

        return results

    def diagnosis_progress(self):
        return self._progress()

    def _has_data(self, patient_data, cde_key):
        try:
            value = self._get_value_from_patient_mongo_data(patient_data, cde_key)
            if value:
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

        for patient_id in self.patient_ids_not_in_mongo:
            results[patient_id] = False
        return results

    def genetic_progress(self):
        return self._progress(progress_type=ProgressType.GENETIC)

    def diagnosis_currency(self, num_days=365):
        results = {}
        logger.debug("mongo data %s" % self.mongo_data)
        for patient_data in self.mongo_data:
            results[
                patient_data["django_id"]] = self.data_currency_one_patient(
                patient_data,
                self.diagnosis_forms,
                num_days)

        for patient_id in self.patient_ids_not_in_mongo:
            results[patient_id] = False

        return results

    def data_currency_one_patient(self, patient_data, form_models, days=365):
        time_window_start = datetime.datetime.now() - datetime.timedelta(days=days)
        for form_model in form_models:
            if self._form_is_current(form_model, patient_data, time_window_start):
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

    def data_modules(self):
        results = {}
        for patient_data in self.mongo_data:
            content = ''

            if not self.viewable_forms:
                content = "No modules available"

            for form in self.viewable_forms:
                if form.is_questionnaire:
                    continue
                is_current = self._form_is_current(form, patient_data)
                flag = "images/%s.png" % ("tick" if is_current else "cross")

                url = reverse('registry_form', args=(
                    self.registry_model.code, form.id, patient_data['django_id']))
                link = "<a href=%s>%s</a>" % (url, nice_name(form.name))
                label = nice_name(form.name)

                to_form = link
                if self.user.is_working_group_staff:
                    to_form = label

                if form.has_progress_indicator:
                    src = static(flag)
                    percentage = self._form_progress_one_form(form, patient_data)
                    content += "<img src=%s> <strong>%d%%</strong> %s</br>" % (
                        src, percentage, to_form)
                else:
                    content += "<img src=%s> %s</br>" % (static(flag), to_form)

            html = "<button type='button' class='btn btn-primary btn-xs' data-toggle='popover' data-content='%s' id='data-modules-btn'>Show</button>" % content
            results[patient_data["django_id"]] = html

        for patient_id in self.patient_ids_not_in_mongo:
            p = Patient.objects.get(id=patient_id)
            results[patient_id] = self.patient_resource._get_data_modules(
                p, self.registry_model.code, self.user)

        return results

    def _form_is_current(
            self,
            form_model,
            patient_data,
            time_window_start=datetime.datetime.now() -
            datetime.timedelta(
            days=365)):
        form_timestamp = self._get_form_timestamp(patient_data, form_model)
        if form_timestamp and form_timestamp >= time_window_start:
            return True
        return False

    def _get_multisection_items(self, form_name, multisection_code, patient_data):
        for form_dict in patient_data["forms"]:
            if form_dict["name"] == form_name:
                for section_dict in form_dict["sections"]:
                    if section_dict["code"] == multisection_code and section_dict["allow_multiple"]:
                        return section_dict["cdes"]

        return []

    def _form_progress_one_form(self, form_model, patient_data):
        completion_list = self.completion_keys_by_form[form_model.name]
        keys = [pair[0] for pair in completion_list]
        percentage = self._progress_for_keys(patient_data, keys)[2]
        return percentage