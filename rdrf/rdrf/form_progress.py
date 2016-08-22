from django.core.urlresolvers import reverse
from django.templatetags.static import static
from rdrf.utils import de_camelcase
from rdrf.mongo_client import construct_mongo_client
from rdrf.utils import mongo_db_name

import math
import logging

logger = logging.getLogger(__name__)


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


def percentage(a, b):
    if b > 0:
        return int(math.floor(100.00 * float(a) / float(b)))
    else:
        return 100


class FormProgressError(Exception):
    pass


def test_value(value):
    if value:
        return True
    else:
        return False


class FormProgress(object):

    def __init__(self, registry_model):
        self.registry_model = registry_model
        self.progress_data = {}
        self.progress_collection = self._get_progress_collection()
        self.progress_cdes_map = self._build_progress_map()
        self.loaded_data = None
        self.current_patient = None
        self.context_model = None

    def _get_forms(self):
        if self.context_model is None:
            return self.registry_model.forms
        elif self.context_model.context_form_group is None:
            return self.registry_model.forms
        else:
            return self.context_form_group.forms

    def _set_current(self, patient_model):
        if self.current_patient is None:
            self.current_patient = patient_model
            self.reset()
        else:
            if self.current_patient.pk != patient_model.pk:
                self.current_patient = patient_model
                self.reset()

    def _get_progress_collection(self):
        db_name = mongo_db_name(self.registry_model.code)
        mongo_client = construct_mongo_client()
        db = mongo_client[db_name]
        return db["progress"]

    def _build_progress_map(self):
        # maps form names to sets of required cde codes
        result = {}
        for form_model in self.registry_model.forms:
            if not form_model.is_questionnaire:
                result[form_model.name] = set([cde_model.code for cde_model in
                                               form_model.complete_form_cdes.all()])
        return result

    def _calculate_form_progress(self, form_model, dynamic_data):
        result = {"required": 0, "filled": 0, "percentage": 0}

        for section_model, cde_model in self._get_progress_cdes(form_model):
            if not section_model.allow_multiple:
                result["required"] += 1
            else:
                num_items = self._get_num_items(form_model, section_model, dynamic_data)
                result["required"] += num_items

            try:
                if not section_model.allow_multiple:
                    value = self._get_value_from_dynamic_data(form_model, section_model, cde_model, dynamic_data)
                    if test_value(value):
                        result["filled"] += 1
                else:
                    values = self._get_values_from_multisection(form_model, section_model, cde_model, dynamic_data)
                    filled_in_values = [value for value in values if test_value(value)]
                    result["filled"] += len(filled_in_values)

            except Exception as ex:
                logger.error("Error getting value for %s %s: %s" % (section_model.code, cde_model.code, ex))

        if result["required"] > 0:
            result["percentage"] = int(100.00 * (float(result["filled"]) / float(result["required"])))
        else:
            result["percentage"] = 0

        return result

    def _get_values_from_multisection(self, form_model, section_model, cde_model, dynamic_data):
        if dynamic_data is None:
            return []
        for form_dict in dynamic_data["forms"]:
            if form_dict["name"] == form_model.name:
                for section_dict in form_dict["sections"]:
                    if section_dict["code"] == section_model.code:
                        values = []
                        items = section_dict["cdes"]
                        for item in items:
                            for cde_dict in item:
                                if cde_dict["code"] == cde_model.code:
                                    values.append(cde_dict["value"])
                        return values
        return []

    def _get_num_items(self, form_model, section_model, dynamic_data):
        if not section_model.allow_multiple:
            return 1
        else:
            if dynamic_data is None:
                return 0
            if "forms" not in dynamic_data:
                return 0
            for form_dict in dynamic_data["forms"]:
                if form_dict["name"] == form_model.name:
                    for section_dict in form_dict["sections"]:
                        if section_dict["code"] == section_model.code:
                            # for multisections the cdes field contains a list
                            # of items, each of which is a list of cde dicts
                            # containing the values for each item
                            items = section_dict["cdes"]
                            return len(items)
        return 0

    def _calculate_form_currency(self, form_model, dynamic_data):
        from datetime import timedelta, datetime
        form_timestamp_key = "%s_timestamp" % form_model.name
        one_year_ago = datetime.now() - timedelta(weeks=52)

        if dynamic_data is None:
            return False

        if form_timestamp_key in dynamic_data:
            form_timeastamp_value = dynamic_data[form_timestamp_key]
            if form_timeastamp_value >= one_year_ago:
                return True

        return False

    def _get_value_from_dynamic_data(self, form_model, section_model, cde_model, dynamic_data):
        # gets value or first value in a multisection
        for form_dict in dynamic_data["forms"]:
            if form_dict["name"] == form_model.name:
                for section_dict in form_dict["sections"]:
                    if section_dict["code"] == section_model.code:
                        if not section_dict["allow_multiple"]:
                            for cde_dict in section_dict["cdes"]:
                                if cde_dict["code"] == cde_model.code:
                                    return cde_dict["value"]
                        else:
                            for section_item in section_dict["cdes"]:
                                for cde_dict in section_item:
                                    if cde_dict["code"] == cde_model.code:
                                        return cde_dict["value"]

    def _get_progress_cdes(self, form_model_required):
        cdes_required = self.progress_cdes_map[form_model_required.name]
        for form_model in self.registry_model.forms:
            if not form_model.is_questionnaire:
                if form_model.name == form_model_required.name:
                    for section_model in form_model.section_models:
                        for cde_model in section_model.cde_models:
                            if cde_model.code in cdes_required:
                                yield section_model, cde_model

    def _get_progress_metadata(self):
        try:
            metadata = self.registry_model.metadata
            if "progress" in metadata:
                return metadata["progress"]
            else:
                # default behaviour - this is the old behaviour
                groups_dict = {"diagnosis": [], "genetic": []}
                for form_model in self.registry_model.forms:
                    if "genetic" in form_model.name.lower():
                        groups_dict["genetic"].append(form_model.name)
                    else:
                        groups_dict["diagnosis"].append(form_model.name)
                return groups_dict
        except Exception as ex:
            logger.error("Error getting progress metadata for registry %s: %s" % (self.registry_model.code,
                                                                                  ex))
            return {}

    def _calculate_form_has_data(self, form_model, dynamic_data):
        if dynamic_data is None:
            return False
        for form_dict in dynamic_data['forms']:
            if form_dict["name"] == form_model.name:
                for section_dict in form_dict["sections"]:
                    if not section_dict["allow_multiple"]:
                        for cde_dict in section_dict["cdes"]:
                            if test_value(cde_dict["value"]):
                                return True
                    else:
                        for item in section_dict["cdes"]:
                            for cde_dict in item:
                                if test_value(cde_dict["value"]):
                                    return True

    def _calculate_form_cdes_status(self, form_model, dynamic_data):
        if dynamic_data is None:
            return {}
        from rdrf.models import CommonDataElement

        def get_name(cde_code):
            cde_model = CommonDataElement.objects.get(code=cde_code)
            return cde_model.name

        cdes_status = {}
        required_cdes = self.progress_cdes_map[form_model.name]
        for cde_code in required_cdes:
            cde_name = get_name(cde_code)
            cdes_status[cde_name] = False

        for form_dict in dynamic_data["forms"]:
            if form_dict["name"] == form_model.name:
                for section_dict in form_dict["sections"]:
                    if not section_dict["allow_multiple"]:
                        for cde_dict in section_dict["cdes"]:
                            if cde_dict["code"] in required_cdes:
                                if cde_dict["value"]:
                                    cde_name = get_name(cde_dict['code'])
                                    cdes_status[cde_name] = True
                    else:
                        for item in section_dict["cdes"]:
                            for cde_dict in item:
                                if cde_dict["code"] in required_cdes:
                                    cde_name = get_name(cde_dict['code'])
                                    if cde_dict["value"]:
                                        cdes_status[cde_name] = True
        return cdes_status

    def _calculate(self, dynamic_data):
        progress_metadata = self._get_progress_metadata()
        if not progress_metadata:
            logger.debug("No progress metadata for %s - nothing to calculate" % self.registry_model.code)
            return

        self._build_progress_map()

        groups_progress = {}
        forms_progress = {}

        for form_model in self.registry_model.forms:
            if not form_model.is_questionnaire:
                form_progress_dict = self._calculate_form_progress(form_model, dynamic_data)
                form_currency = self._calculate_form_currency(form_model, dynamic_data)
                form_has_data = self._calculate_form_has_data(form_model, dynamic_data)
                form_cdes_status = self._calculate_form_cdes_status(form_model, dynamic_data)
                forms_progress[form_model.name] = {"progress": form_progress_dict,
                                                   "current": form_currency,
                                                   "has_data": form_has_data,
                                                   "cdes_status": form_cdes_status}

                for progress_group in progress_metadata:
                    if form_model.name in progress_metadata[progress_group]:

                        if progress_group not in groups_progress:
                            groups_progress[progress_group] = {"required": 0,
                                                               "filled": 0,
                                                               "percentage": 0,
                                                               "current": True,
                                                               "has_data": False}

                        groups_progress[progress_group]["required"] += form_progress_dict["required"]
                        groups_progress[progress_group]["filled"] += form_progress_dict["filled"]
                        groups_progress[progress_group]["current"] = groups_progress[
                            progress_group]["current"] or form_currency
                        groups_progress[progress_group]['has_data'] = groups_progress[
                            progress_group]["has_data"] or form_has_data

        for group_name in groups_progress:
            groups_progress[group_name]["percentage"] = percentage(groups_progress[group_name]["filled"],
                                                                   groups_progress[group_name]["required"])

        # now save the metric in form expected by _get_metric
        result = {}
        for form_name in forms_progress:
            result[form_name + "_form_progress"] = forms_progress[form_name]["progress"]
            result[form_name + "_form_current"] = forms_progress[form_name]["current"]
            result[form_name + "_form_has_data"] = forms_progress[form_name]["has_data"]
            result[form_name + "_form_cdes_status"] = forms_progress[form_name]["cdes_status"]

        for groups_name in groups_progress:
            result[groups_name + "_group_progress"] = groups_progress[groups_name]["percentage"]

            result[groups_name + "_group_current"] = groups_progress[groups_name]["current"]
            result[groups_name + "_group_has_data"] = groups_progress[groups_name]['has_data']

        self.progress_data = result

    def _get_query(self, patient_model, context_model):
        query = {"django_id": patient_model.pk, "django_model": patient_model.__class__.__name__}
        if context_model:
            context_id = context_model.id
            query["context_id"] = context_id

        return query

    def _load(self, patient_model, context_model=None):
        query = self._get_query(patient_model, context_model)
        self.loaded_data = self.progress_collection.find_one(query)
        if self.loaded_data is None:
            self.loaded_data = {}
        return self.loaded_data

    def _get_metric(self, metric, patient_model, context_model=None):
        self._set_current(patient_model)  # if new model passed in this causes progress data reload
        self.context_model = context_model
        # eg _get_metric((SomeFormModel, "progress"), fred, None)
        # or _get_metric("diagnosis_current", fred, context23) etc

        if self.loaded_data is None:
            self._load(patient_model, context_model)

        if metric == "diagnosis_group_progress":
            return self.loaded_data.get("diagnosis_group_progress", 0)
        elif metric == "diagnosis_group_current":
            return self.loaded_data.get("diagnosis_group_current", False)
        elif metric == "genetic_group_has_data":
            return self.loaded_data.get("genetic_group_has_data", False)
        elif isinstance(metric, tuple):
            form_model, tag = metric
            if tag == "progress":
                return self.loaded_data.get(form_model.name + "_form_progress", {})
            elif tag == "current":
                return self.loaded_data.get(form_model.name + "_form_current", False)
            elif tag == "cdes_status":
                initial_completion_status_cdes = {cde_model.name: False for cde_model
                                                  in form_model.complete_form_cdes.all()}
                return self.loaded_data.get(form_model.name + "_form_cdes_status", initial_completion_status_cdes)
            else:
                raise FormProgressError("Unknown metric: %s" % metric)
        else:
            raise FormProgressError("Unknown metric: %s" % metric)

    def _get_viewable_forms(self, user):
        form_container_model = self._get_form_container_model()

        return [f for f in form_container_model.forms if not f.is_questionnaire and
                user.can_view(f)]

        # return [f for f in RegistryForm.objects.filter(registry=self.registry_model).order_by(
        #    'position') if not f.is_questionnaire and user.can_view(f)]

    def _get_form_container_model(self):
        if self.context_model is not None:
            if self.context_model.context_form_group:
                return self.context_model.context_form_group
        return self.registry_model

    # Public API
    def reset(self):
        self.loaded_data = None

    def get_form_progress_dict(self, form_model, patient_model, context_model=None):
        # returns a dict of required filled percentage numbers
        return self._get_metric((form_model, "progress"), patient_model, context_model)

    def get_form_progress(self, form_model, patient_model, context_model=None):
        d = self.get_form_progress_dict(form_model, patient_model, context_model)
        if "percentage" in d:
            return d["percentage"]
        else:
            return 0

    def get_form_currency(self, form_model, patient_model, context_model=None):
        return self._get_metric((form_model, "current"), patient_model, context_model)

    def get_form_cdes_status(self, form_model, patient_model, context_model=None):
        return self._get_metric((form_model, "cdes_status"), patient_model, context_model)

    def get_group_progress(self, group_name, patient_model, context_model=None):
        metric_name = "%s_group_progress" % group_name
        return self._get_metric(metric_name, patient_model, context_model)

    def get_group_currency(self, group_name, patient_model, context_model=None):
        metric_name = "%s_group_current" % group_name
        return self._get_metric(metric_name, patient_model, context_model)

    def get_group_has_data(self, group_name, patient_model, context_model=None):
        metric_name = "%s_group_has_data" % group_name
        return self._get_metric(metric_name, patient_model, context_model)

    def get_data_modules(self, user, patient_model, context_model):
        self._set_current(patient_model)
        viewable_forms = self._get_viewable_forms(user)
        content = ""
        if not viewable_forms:
            content = "No modules available"
        else:
            for form in viewable_forms:
                is_current = self.get_form_currency(form, patient_model, context_model)
                flag = "images/%s.png" % ("tick" if is_current else "cross")
                url = reverse('registry_form', args=(self.registry_model.code,
                                                     form.id, patient_model.pk,
                                                     context_model.pk))
                link = "<a href=%s>%s</a>" % (url, form.nice_name)
                label = form.nice_name
                to_form = link
                if user.is_working_group_staff:
                    to_form = label

                if form.has_progress_indicator:
                    src = static(flag)
                    percentage = self.get_form_progress(form, patient_model, context_model)
                    content += "<img src=%s> <strong>%d%%</strong> %s</br>" % (src, percentage, to_form)
                else:
                    content += "<img src=%s> %s</br>" % (static(flag), to_form)

        html = "<button type='button' class='btn btn-primary btn-xs' " + \
               "data-toggle='popover' data-content='%s' id='data-modules-btn'>Show</button>" % content
        return html

    #########################################################################################
    # save progress
    def save_progress(self, patient_model, dynamic_data, context_model=None):
        if not dynamic_data:
            return self.progress_data
        self._calculate(dynamic_data)
        query = self._get_query(patient_model, context_model)
        record = self.progress_collection.find_one(query)
        if record:
            mongo_id = record['_id']
            self.progress_collection.update({'_id': mongo_id}, {"$set": self.progress_data}, upsert=False)
        else:
            record = query
            record.update(self.progress_data)
            self.progress_collection.insert(record)

        return self.progress_data

    # a convenience method
    def save_for_patient(self, patient_model, context_model=None):
        self.reset()
        from rdrf.dynamic_data import DynamicDataWrapper
        wrapper = DynamicDataWrapper(patient_model)
        dynamic_data = wrapper.load_dynamic_data(self.registry_model.code, "cdes", flattened=False)
        return self.save_progress(patient_model, dynamic_data, context_model)
