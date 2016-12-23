import datetime
from operator import itemgetter
from itertools import zip_longest
import logging
from django.core.files.uploadedfile import InMemoryUploadedFile

from . import filestorage
from .file_upload import FileUpload, wrap_gridfs_data_for_form
from .models import Registry, Modjgo
from .utils import get_code, models_from_mongo_key, is_delimited_key, mongo_key, is_multisection
from .utils import is_file_cde, is_multiple_file_cde, is_uploaded_file

logger = logging.getLogger(__name__)


class FormParsingError(Exception):
    pass


class KeyValueMissing(Exception):
    pass


def find_sections(doc, form_name=None, section_code=None,
                  formp=None, sectionp=None,
                  multisection=False):
    """
    Iterates through form sections of a mongo doc.
      form_name: Filter by form
      section_code: Filter by code
      formp: predicate function(form_dict, index)
      sectionp: predicate function(section_dict, index | (index, index))
      multisection: whether to find multisections or single sections
    """
    formp = formp or (lambda f, i: True)
    sectionp = sectionp or (lambda s, i: True)

    for f, form in enumerate(doc.get("forms") or []):
        if (form_name is None or
                (form.get("name") == form_name and formp(form, f))):
            for s, section in enumerate(form.get("sections") or []):
                if ((section_code is None or
                     section.get("code") == section_code) and
                        bool(multisection) == bool(section.get("allow_multiple"))):
                    if multisection:
                        for s2, section2 in enumerate(section.get("cdes") or []):
                            product = dict(section)
                            product["cdes"] = section2
                            if sectionp(product, (s, s2)):
                                yield product
                    elif sectionp(section, s):
                        yield section


def find_cdes(doc, form_name=None, section_code=None, cde_code=None,
              formp=None, sectionp=None, cdep=None,
              multisection=False):
    """
    Iterates through CDEs stored in a mongo doc.
    """
    cdep = cdep or (lambda c, i: True)

    sections = find_sections(doc, form_name, section_code, formp, sectionp,
                             multisection=multisection)
    for section in sections:
        for c, cde in enumerate(section.get("cdes") or []):
            if (cde_code is None or
                    (cde.get("code") == cde_code and cdep(cde, c))):
                yield cde

section_allow_multiple = lambda s, i: bool(s.get("allow_multiple"))
section_not_allow_multiple = lambda s, i: not s.get("allow_multiple")


def get_mongo_value(registry_code, nested_data, delimited_key,
                    multisection_index=None):
    """
    Grabs a CDE value out of the mongo document.
      nested_data: mongo document dict
      delimited_key: form_name____section_code____cde_code
    """
    registry_model = Registry.objects.get(code=registry_code)
    form_model, section_model, cde_model = models_from_mongo_key(registry_model, delimited_key)

    if multisection_index is None:
        sectionp = None
    else:
        sectionp = lambda s, ij: ij[1] == multisection_index

    cdes = find_cdes(nested_data, form_model.name, section_model.code,
                     cde_model.code, sectionp=sectionp,
                     multisection=multisection_index is not None)
    for cde in cdes:
        return cde["value"]
    return None


def update_multisection_file_cdes(registry_code,
                                  multisection_code, form_section_items,
                                  form_model, existing_nested_data, index_map):

    logger.debug("****************** START UPDATE MULTISECTION FILE CDES ****************************")
    logger.debug("updating any gridfs files in multisection %s" % multisection_code)

    updates = []

    for item_index, section_item_dict in enumerate(form_section_items):
        logger.debug("checking new saved section %s" % item_index)

        for key, value in section_item_dict.items():
            cde_code = get_code(key)
            if is_file_cde(cde_code):
                existing_value = get_mongo_value(registry_code, existing_nested_data, key,
                                                 multisection_index=item_index)
                if is_multiple_file_cde(cde_code):
                    new_val = DynamicDataWrapper.handle_file_uploads(registry_code, key, value, existing_value)
                else:
                    new_val = DynamicDataWrapper.handle_file_upload(registry_code, key, value, existing_value)
                updates.append((item_index, key, new_val))

    for index, key, value in updates:
        form_section_items[index][key] = value

    logger.debug("****************** END UPDATE MULTISECTION FILE CDES ****************************")
    return form_section_items


def build_form_data(data):
    """
    Converts clinical json data to the flattened form, suitable for
    use in template view context.
    :param data: json field value dict
    :return: a dictionary of nested or flattened data for this instance
    """
    flattened = {}
    for k in data:
        if k != "forms":
            flattened[k] = data[k]

    for form_dict in data["forms"]:
        for section_dict in form_dict["sections"]:
            if not section_dict["allow_multiple"]:
                for cde_dict in section_dict["cdes"]:
                    value = cde_dict["value"]
                    delimited_key = mongo_key(form_dict["name"], section_dict["code"], cde_dict["code"])
                    flattened[delimited_key] = value
            else:
                multisection_code = section_dict["code"]
                flattened[multisection_code] = []
                multisection_items = section_dict["cdes"]
                for cde_list in multisection_items:
                    d = {}
                    for cde_dict in cde_list:
                        delimited_key = mongo_key(form_dict["name"], section_dict["code"], cde_dict["code"])
                        d[delimited_key] = cde_dict["value"]
                    flattened[multisection_code].append(d)

    return flattened


def parse_form_data(registry, form, data,
                    existing_record=None, is_multisection=False,
                    parse_all_forms=False, django_instance=None):
    """
    This class takes a bag of values with keys like:
    Takes a bag of values with keys like:
      form_name____section_code____cde_code
    and converts them into a nested document suitable for storing in
    the mongodb.

    This is more or less the opposite of `build_form_data`.
    """
    return FormDataParser(registry, form, data,
                          existing_record, is_multisection,
                          parse_all_forms, django_instance).nested_data


class FormDataParser(object):
    """
    The nested document is accessed by the `nested_data` property.

    I think this class should be converted into a single function
    (with nested functions) because it's used like a function not like
    an object.
    """
    def __init__(self,
                 registry_model,
                 form_model,
                 form_data,
                 existing_record=None,
                 is_multisection=False,
                 parse_all_forms=False,
                 django_instance=None):
        self.registry_model = registry_model
        self.form_data = form_data
        self.parsed_data = {}
        self.parsed_multisections = {}
        self.global_timestamp = None
        self.form_timestamps = {}
        self.mongo_id = None
        self.existing_record = existing_record
        self.is_multisection = is_multisection
        self.form_model = form_model
        self.custom_consents = None
        self.address_data = None
        self.parse_all_forms = parse_all_forms

        if django_instance:
            self.django_id = django_instance.pk
            self.django_model = django_instance.__class__.__name__
        else:
            self.django_id = None
            self.django_model = None

    def update_timestamps(self, form_model):
        t = datetime.datetime.now()
        form_timestamp = form_model.name + "_timestamp"
        self.global_timestamp = t
        self.form_timestamps[form_timestamp] = t

    @property
    def nested_data(self):
        if not self.parse_all_forms:
            self._parse()
        else:
            self._parse_all_forms()

        d = self.existing_record or {"forms": []}

        if self.django_id:
            d["django_id"] = self.django_id

        if self.django_model:
            d["django_model"] = self.django_model

        if self.mongo_id:
            d["mongo_id"] = self.mongo_id

        if self.custom_consents:
            d["custom_consent_data"] = self.custom_consents

        if self.address_data:
            d["PatientDataAddressSection"] = self.address_data

        if self.global_timestamp:
            d["timestamp"] = self.global_timestamp

        for form_timestamp in self.form_timestamps:
            d[form_timestamp] = self.form_timestamps[form_timestamp]

        for (form_model, section_model, cde_model), value in self.parsed_data.items():
            if not section_model.allow_multiple:
                cde_dict = self._get_cde_dict(form_model, section_model, cde_model, d)
                logger.debug("existing cde dict = %s" % cde_dict)
                if self._is_file(value):
                    logger.debug("nested data - file value = %s" % value)
                    # should check here is we're updating a file in gridfs - the old file needs to be deleted
                    value = self._get_gridfs_value(value)
                    logger.debug("value is now: %s" % value)

                cde_dict["value"] = value

        for (form_model, section_model), items_list in self.parsed_multisections.items():
            section_dict = self._get_section_dict(form_model, section_model, d)
            section_dict["allow_multiple"] = True
            section_dict["cdes"] = items_list

        return d

    def _is_file(self, value):
        return isinstance(value, InMemoryUploadedFile)

    def _get_gridfs_value(self, inmemory_uploaded_file):
        return None

    def _parse_timestamps(self):
        for key in self.form_data:
            if key == "timestamp":
                self.global_timestamp = self.form_data[key]
            elif key.endswith("_timestamp"):
                self.form_timestamps[key] = self.form_data[key]

    def _parse_all_forms(self):
        # used in questionnaire approval handling where all form data was being saved in one go
        # generated questionnaire gets fanned out to all forms
        for key in self.form_data:
            if key == "timestamp":
                self.global_timestamp = self.form_data[key]
            elif key.endswith("_timestamp"):
                self.form_timestamps[key] = self.form_data[key]
            elif key == "custom_consent_data":
                pass
            elif key == "PatientDataAddressSection":
                pass
            elif is_multisection(key):
                self._parse_multisection(key)
            elif is_delimited_key(key):
                form_model, section_model, cde_model = models_from_mongo_key(self.registry_model, key)
                value = self.form_data[key]
                self.parsed_data[(form_model, section_model, cde_model)] = self._parse_value(value)

    def _parse_multisection(self, multisection_code):
        self._parse_timestamps()
        the_form_model = None
        the_section_model = None
        multisection_item_list = self.form_data[multisection_code]
        if len(multisection_item_list) == 0:
            from rdrf.models import Section
            section_model = Section.objects.get(code=multisection_code)
            self.parsed_multisections[(self.form_model, section_model)] = []
            return
        items = []
        for item_dict in multisection_item_list:
            if "DELETE" in item_dict and item_dict["DELETE"]:
                continue
            item = []
            for key in item_dict:
                if is_delimited_key(key):
                    value = item_dict[key]
                    form_model, section_model, cde_model = models_from_mongo_key(self.registry_model, key)
                    if the_form_model is None:
                        the_form_model = form_model
                    if the_section_model is None:
                        the_section_model = section_model

                    value = self._parse_value(value)

                    cde_dict = {"code": cde_model.code, "value": value}
                    item.append(cde_dict)
            items.append(item)
        self.parsed_multisections[(the_form_model, the_section_model)] = items

    def _parse_value(self, value):
        if isinstance(value, FileUpload):
            logger.debug("FileUpload wrapper - returning the gridfs dict!")
            return value.mongo_data
        elif isinstance(value, InMemoryUploadedFile):
            logger.debug("InMemoryUploadedFile returning None")
            return None
        elif isinstance(value, list):
            # list of files -- parse each one
            return [self._parse_value(v) for v in value]
        else:
            # return the bare value
            return value

    def _parse(self):
        if not self.is_multisection:
            for key in self.form_data:
                logger.debug("FormDataParser: key = %s" % key)
                if key == "timestamp":
                    self.global_timestamp = self.form_data[key]
                elif key.endswith("_timestamp"):
                    self.form_timestamps[key] = self.form_data[key]
                elif key == "custom_consent_data":
                    self.custom_consents = self.form_data[key]
                elif key == "PatientDataAddressSection":
                    self.address_data = self.form_data[key]
                elif is_delimited_key(key):
                    form_model, section_model, cde_model = models_from_mongo_key(self.registry_model, key)
                    value = self.form_data[key]
                    self.parsed_data[(form_model, section_model, cde_model)] = self._parse_value(value)
                else:
                    logger.debug("don't know how to parse key: %s" % key)
        else:
            # multisections extracted from the form like this (ugh):
            # the delimited keys  will(should) always be cdes from the same form and section
            #{u'testmultisection': [
            # {u'DELETE': False, u'testform____testmultisection____DM1FatigueTV': u'DM1FatigueDozingNever',
            #  u'testform____testmultisection____DM1FatigueDrug': u'd1'},
            #
            # {u'DELETE': False, u'testform____testmultisection____DM1FatigueTV': u'DM1FatigueDozingSlightChance', u'testform____testmultisection____DM1FatigueDrug': u'd2'}]}

            multisection_code = self._get_multisection_code()

            self._parse_multisection(multisection_code)

    def _get_multisection_code(self):
        # NB this assumes we're only parsing multisection forms one  at at time
        from rdrf.utils import is_multisection
        for key in self.form_data:
            if is_multisection(key):
                return key

    def _get_cde_dict(self, form_model, section_model, cde_model, data):
        section_dict = self._get_section_dict(form_model, section_model, data)
        for cde_dict in section_dict["cdes"]:
            if cde_dict["code"] == cde_model.code:
                return cde_dict
        cde_dict = {"code": cde_model.code, "value": None}
        section_dict["cdes"].append(cde_dict)
        return cde_dict

    def _get_section_dict(self, form_model, section_model, data):
        form_dict = self._get_form_dict(form_model, data)
        for section_dict in form_dict["sections"]:
            if section_dict["code"] == section_model.code:
                return section_dict
        section_dict = {"code": section_model.code, "cdes": [], "allow_multiple": section_model.allow_multiple}
        form_dict["sections"].append(section_dict)
        return section_dict

    def _get_form_dict(self, form_model, data):
        for form_dict in data["forms"]:
            if form_dict["name"] == form_model.name:
                return form_dict
        form_dict = {"name": form_model.name, "sections": []}
        data["forms"].append(form_dict)
        return form_dict


class DynamicDataWrapper(object):

    """
    Utility class to save and load dynamic data for a Django model object
    Usage:
    E.G. wrapper = DynamicDataWrapper(patient)
    data = wrapper.load_dynamic_data("sma", "cdes)
    ... modify data to new_data
    wrapper.save_dynamic_data("sma","cdes", new_data)

    """
    REGISTRY_SPECIFIC_PATIENT_DATA_COLLECTION = "registry_specific_patient_data"

    def __init__(
            self,
            obj,
            filestore_class=None,
            rdrf_context_id=None):
        # When set to True by integration tests, uses testing mongo database
        if rdrf_context_id == "add":
            # Create context model just before saving to mongo
            self.CREATE_MODE = True
        else:
            self.CREATE_MODE = False
        self.testing = False
        self.obj = obj
        self.django_id = obj.pk
        self.django_model = obj.__class__
        # when saving data to Mongo this field allows timestamp to be recorded
        self.current_form_model = None
        self.rdrf_context_id = rdrf_context_id

        # holds reference to the complete data record for this object
        self.patient_record = None

    def __str__(self):
        return "Dynamic Data Wrapper for %s id=%s" % (self.obj.__class__.__name__, self.obj.pk)

    def _get_record(self, registry, collection_name, filter_by_context=True):
        qs = Modjgo.objects.collection(registry, collection_name)
        return qs.find(self.obj, self.rdrf_context_id if filter_by_context else None)

    def _make_record(self, registry_code, collection_name, data=None, **kwargs):
        data = dict(data or {})
        data["context_id"] = self.rdrf_context_id
        return Modjgo.for_obj(self.obj, registry_code=registry_code,
                              collection=collection_name, data=data, **kwargs)

    def has_data(self, registry_code):
        return self._get_record(registry_code, "cdes").exists()

    def load_dynamic_data(self, registry, collection_name, flattened=True):
        """
        :param registry: e.g. sma or dmd
        :param collection_name: e.g. cde or hpo
        :param flattened: use flattened to get data in a form suitable for the view
        :return: a dictionary of nested or flattened data for this instance
        """
        nested_data = self._get_record(registry, collection_name).data().first()

        if flattened and nested_data is not None:
            return build_form_data(nested_data)
        else:
            return nested_data

    def get_cde_val(self, registry_code, form_name, section_code, cde_code):
        data = self._get_record(registry_code, "cdes")
        return data.cde_val(form_name, section_code, cde_code)

    def get_cde_history(self, registry_code, form_name, section_code, cde_code):
        def fmt(snapshot):
            return {
                "timestamp": datetime.datetime.strptime(snapshot["timestamp"][:19], "%Y-%m-%d %H:%M:%S"),
                "value": self._find_cde_val(snapshot["record"], registry_code,
                                            form_name, section_code,
                                            cde_code),
                "id": str(snapshot["_id"]),
            }

        def collapse_same(snapshots):
            prev = {"": None}  # nonlocal works in python3

            def is_different(snap):
                diff = prev[""] is None or snap["value"] != prev[""]["value"]
                prev[""] = snap
                return diff
            return list(filter(is_different, snapshots))
        record_query = self._get_record(registry_code, "history", filter_by_context=False)
        record_query = record_query.find(record_type="snapshot")
        data = map(fmt, record_query.data())
        return collapse_same(sorted(data, key=itemgetter("timestamp")))

    def load_contexts(self, registry_model):
        logger.debug("registry model = %s" % registry_model)
        if not registry_model.has_feature("contexts"):
            raise Exception("Registry %s does not support use of contexts" % registry_model.code)

        logger.debug("registry supports contexts so retreiving")
        from rdrf.models import RDRFContext
        django_model = self.obj.__class__.__name__
        mongo_query = {"django_id": self.django_id,
                       "django_model": django_model}
        logger.debug("query = %s" % mongo_query)

        projection = {"rdrf_context_id": 1, "_id": 0}

        logger.debug("projection = %s" % projection)

        cdes_collection = self._get_collection(registry_model.code, "cdes")

        context_ids = [d["rdrf_context_id"] for d in cdes_collection.find(mongo_query, projection)]
        logger.debug("context_ids = %s" % context_ids)
        rdrf_context_models = []
        for context_id in context_ids:
            try:
                rdrf_context_model = RDRFContext.objects.get(pk=int(context_id))
                rdrf_context_models.append(rdrf_context_model)
            except RDRFContext.DoesNotExist:
                logger.error("Context %s for %s %s does not exist?" % (context_id, django_model, self.obj.pk))

        logger.debug("contexts = %s" % rdrf_context_models)
        return rdrf_context_models

    def load_registry_specific_data(self, registry_model=None):
        data = {}
        if registry_model is None:
            return data
        record_query = self._get_record(registry_model.code, self.REGISTRY_SPECIFIC_PATIENT_DATA_COLLECTION)
        registry_data = record_query.data().first()
        if registry_data:
            for k in ['django_id', '_id', 'django_model']:
                if k in registry_data:
                    del registry_data[k]
            data[registry_model.code] = registry_data

        for registry_code in data:
            wrap_gridfs_data_for_form(registry_model, data[registry_code])
        logger.debug("registry_specific_data after wrapping for files = %s" % data)
        return data

    def save_registry_specific_data(self, data):
        logger.debug("saving registry specific mongo data: %s" % data)
        for reg_code in data:
            registry_data = data[reg_code]
            if not registry_data:
                continue
            query = (reg_code, "registry_specific_patient_data")
            record = self._get_record(*query).first()
            if not record:
                record = self._make_record(*query)
            record.data.update(registry_data)
            record.save()

    def _is_section_code(self, code):
        # Supplied code will be non-delimited
        from .models import Section
        return Section.objects.filter(code=code).exists()

    @staticmethod
    def handle_file_upload(registry_code, key, value, current_value):
        if value is False and current_value:
            # Django uses a "clear" checkbox value of False to indicate file should be removed
            # we need to delete the file but not here
            logger.debug("User cleared %s - file will be deleted" % key)
            to_delete = current_value
            value = None
        elif value is None:
            # No file upload means keep the current value
            logger.debug(
                "User did not change file %s - existing_record will not be updated" % key)
            to_delete = None
            value = current_value
        elif is_uploaded_file(value):
            # A file was uploaded.
            # Store file and convert value into a file wrapper
            to_delete = current_value
            value = filestorage.store_file_by_key(registry_code, None, key, value)
        else:
            to_delete = None

        if to_delete:
            filestorage.delete_file_wrapper(to_delete)

        return value

    @classmethod
    def handle_file_uploads(cls, registry_code, key, value, current_value):
        updated = [cls.handle_file_upload(registry_code, key, val, cur) for
                   val, cur in zip_longest(value, current_value or [])]
        return list(filter(bool, updated))

    def _update_files_in_gridfs(self, existing_record, registry, new_data, index_map):
        for key, value in new_data.items():
            cde_code = get_code(key)
            if is_file_cde(cde_code):
                existing_value = get_mongo_value(registry, existing_record, key)
                if is_multiple_file_cde(cde_code):
                    new_data[key] = self.handle_file_uploads(registry, key, value, existing_value)
                else:
                    new_data[key] = self.handle_file_upload(registry, key, value, existing_value)

            elif (self._is_section_code(key) and self.current_form_model and
                  index_map is not None):
                new_data[key] = update_multisection_file_cdes(registry, key, value,
                                                              self.current_form_model,
                                                              existing_record, index_map)

    def update_dynamic_data(self, registry_model, cdes_record):
        logger.info("About to update %s in %s with new cdes_record %s" % (self.obj,
                                                                           registry_model,
                                                                           cdes_record))
        # replace entire cdes record with supplied one
        # assumes structure correct ..

        from rdrf.models import Modjgo
        from rdrf.models import RDRFContext

        # assumes context_id in cdes_record
        if "context_id" in cdes_record:
            context_id = cdes_record["context_id"]
        else:
            raise Exception("expected context_id in cdes_record")

        try:
            cdes_modjgo = Modjgo.objects.get(registry_code=registry_model.code,
                                             collection="cdes",
                                             data__django_id=self.obj.pk,
                                             data__django_model=self.obj.__class__.__name__,
                                             data__context_id=context_id)
            
                                                
            cdes_modjgo.data.update(cdes_record)

        except Modjgo.DoesNotExist:
            cdes_modjgo = Modjgo.for_obj(self.obj,
                                         registry_code=registry_model.code,
                                         collection="cdes",
                                         data=cdes_record)


        from rdrf.jsonb import _convert_datetime_to_str
        # Not sure why I have to do this explicitly
        _convert_datetime_to_str(cdes_modjgo.data)
        cdes_modjgo.save()
        

    def delete_patient_record(self, registry_model, context_id):
        self.rdrf_context_id = context_id
        logger.info("delete_patient_record called: patient %s registry %s context %s" % (self.obj,
                                                                                         registry_model,
                                                                                         context_id))

        # used _only_ when trying to emulate a roll-back to no data after an exception  in questionnaire handling
        if self.obj.__class__.__name__ != 'Patient':
            raise Exception("can't delete non-patient record")

        collection = self._get_collection(registry_model.code, "cdes")
        logger.debug("collection = %s" % collection)

        filter = {"django_id": self.obj.pk,
                  "django_model": 'Patient',
                  "context_id": context_id}

        logger.info("Deleting patient record from mongo for rollback: %s" % filter)
        try:
            collection.remove(filter)
            logger.info("deleted OK..")
        except Exception as ex:
            logger.error("Error deleting record: %s" % ex)

    def _create_context_model_on_fly(self):
        assert self.CREATE_MODE, "Must be in CREATE MODE"
        assert self.rdrf_context_id == "add", "Must be adding"
        assert self.current_form_model is not None, "Must be on a form"
        registry_model = self.current_form_model.registry
        # locate the multiple form group this form (must) be in
        form_group = None
        for cfg in registry_model.multiple_form_groups:
            form_models = cfg.form_models
            if len(form_models) == 1:
                if form_models[0].pk == self.current_form_model.pk:
                    form_group = cfg
                    break

        if form_group is None:
            raise Exception("Cannot add this form!")

        from django.contrib.contenttypes.models import ContentType
        PATIENT_CONTENT_TYPE = ContentType.objects.get(model='patient')
        from rdrf.models import RDRFContext
        context_model = RDRFContext(registry=registry_model,
                                    object_id=self.obj.pk,
                                    content_type=PATIENT_CONTENT_TYPE)
        context_model.context_form_group = form_group
        context_model.save()
        return context_model.pk

    def save_dynamic_data(self, registry, collection_name, form_data, multisection=False, parse_all_forms=False,
                          index_map=None, additional_data=None):
        self._convert_date_to_datetime(form_data)

        if self.CREATE_MODE:
            record = None
        else:
            record = self._get_record(registry, collection_name).first()

        form_data["timestamp"] = datetime.datetime.now()

        if self.current_form_model:
            form_timestamp_key = "%s_timestamp" % self.current_form_model.name
            form_data[form_timestamp_key] = form_data["timestamp"]

        if not record:
            logger.debug("saving dynamic data - new record")
            record = self._make_record(registry, collection_name)
            record.data["forms"] = []

        self._update_files_in_gridfs(record.data, registry, form_data, index_map)

        nested_data = parse_form_data(Registry.objects.get(code=registry),
                                      self.current_form_model,
                                      form_data,
                                      existing_record=record.data,
                                      is_multisection=multisection,
                                      parse_all_forms=parse_all_forms,
                                      django_instance=self.obj)

        if additional_data is not None:
            nested_data.update(additional_data)

        if record.id is None and self.CREATE_MODE:
            # create context_model NOW  to get context_id
            # CREATE MODE is used ONLY by multiple context form groups to enable cancellation in GUI
            context_id = self._create_context_model_on_fly()
            nested_data["context_id"] = context_id
            # not any subsequent calls won't try to create new context models
            self.CREATE_MODE = False
            self.rdrf_context_id = context_id

        record.data.update(nested_data)
        record.save()

    def _save_longitudinal_snapshot(self, registry_code, record):
        try:
            timestamp = str(datetime.datetime.now())
            patient_id = record.data['django_id']
            snapshot = {"django_id": patient_id,
                        "django_model": record.data.get("django_model", None),
                        "registry_code": registry_code,
                        "record_type": "snapshot",
                        "timestamp": timestamp,
                        "record": record.data,
                        }
            history = self._make_record(registry_code, "history", data=snapshot)
            history.save()
            logger.debug("snapshot added for %s patient %s timestamp %s" % (registry_code, patient_id, timestamp))

        except Exception as ex:
            logger.error("Couldn't add to history for patient %s: %s" % (patient_id, ex))

    def save_snapshot(self, registry_code, collection_name):
        record = self._get_record(registry_code, collection_name).first()
        if record is not None:
            self._save_longitudinal_snapshot(registry_code, record)

    def save_form_progress(self, registry_code, context_model=None):
        from rdrf.form_progress import FormProgress
        registry_model = Registry.objects.get(code=registry_code)
        form_progress = FormProgress(registry_model)
        dynamic_data = self.load_dynamic_data(registry_code, "cdes", flattened=False)
        return form_progress.save_progress(self.obj, dynamic_data, context_model)

    def _convert_date_to_datetime(self, data):
        """
        pymongo doesn't allow saving datetime.Date

        :param data: dictionary of CDE codes --> values
        :return:
        """
        if isinstance(data, list):
            for x in data:
                self._convert_date_to_datetime(x)
        elif hasattr(data, "items"):
            for k, value in data.items():
                if isinstance(value, datetime.date):
                    data[k] = datetime.datetime(value.year, value.month, value.day)
                else:
                    # recurse on multisection data
                    self._convert_date_to_datetime(value)

    def delete_patient_data(self, registry_model, patient_model):
        cdes = self._get_collection(registry_model, "cdes")
        cdes.remove({"django_id": patient_model.pk, "django_model": "Patient"})

    def get_nested_cde(self, registry_code, form_name, section_code, cde_code):
        # fixme: clean this up
        for form_dict, section_dict, item in self.iter_cdes(registry_code):
            if form_dict["name"] == form_name:
                if section_dict["code"] == section_code:
                    if not section_dict["allow_multiple"]:
                        if item["code"] == cde_code:
                            return item["value"]
                    else:
                        results = []
                        for cde in item:
                            if cde["code"] == cde_code:
                                results.append(cde["value"])
                        return results

    def iter_cdes(self, registry_code):
        data = self.load_dynamic_data(registry_code, "cdes", flattened=False)
        if "forms" in data:
            for form_dict in data["forms"]:
                for section_dict in form_dict['sections']:
                    for cde_dict in section_dict["cdes"]:
                        yield form_dict, section_dict, cde_dict

    def get_form_timestamp(self, registry_form):
        qs = self._get_record(registry_form.registry.code, "cdes")
        qs = qs.exclude(data__timestamp="")
        qs = qs.exclude(data__timestamp__isnull=True)
        return qs.values_list("data__timestamp").first()
