from django.core.files.uploadedfile import InMemoryUploadedFile
from rdrf.mongo_client import construct_mongo_client
import logging
from rdrf.utils import get_code, mongo_db_name, models_from_mongo_key, is_delimited_key, mongo_key, is_multisection
from rdrf.utils import is_file_cde, is_uploaded_file

from django.conf import settings
from datetime import datetime
from rdrf.file_upload import FileUpload
from . import filestorage
from copy import deepcopy
from operator import itemgetter



logger = logging.getLogger(__name__)


class FormParsingError(Exception):
    pass


class KeyValueMissing(Exception):
    pass

class MultisectionGridFSFileHandler(object):
    def __init__(self,
                 gridfs_filestore,
                 registry_code,
                 form_model,
                 multisection_code,
                 form_section_items,
                 existing_nested_data,
                 index_map):

        self.original_data = deepcopy(existing_nested_data)
        self.gridfs_filestore = gridfs_filestore
        self.registry_code = registry_code
        self.form_model = form_model
        self.multisection_code = multisection_code
        self.form_section_items = form_section_items # list of section dicts in this multisection
        self.existing_nested_data = existing_nested_data
        self.index_map = index_map  # if sections have been deleted,

        # bookkeeping of gridfs file ids
        self.existing_file_ids = set([])

        self.added_file_ids = set([])
        self.deleted_file_ids = set([])
        self.unchanged_file_ids = set([])


    def _add_file(self, item_index, key, file_object):
        # Put an uploaded file into gridfs and return a wrapper dictionary  which is stored against the key mongo
        # After adding the file to gridfs , the original uploaded file object is replaced by a dictionary
        # referencing the gridfs file ( a gridfs_ref_dict )
        # the passed in new_section_items_from_form list is updated with this dictionary
        # this will be stored in mongo

        logger.debug("adding a file to gridfs for %s %s item %s key %s" % (self.form_model.name,
                                                                           self.multisection_code,
                                                                           item_index,
                                                                           key))

        gridfs_ref_dict = filestorage.store_file_by_key(
            self.registry_code, None, key, file_object)

        logger.debug("key %s will be updated with %s" % (key, gridfs_ref_dict))

        logger.debug("locating the section item to update with the gridfs_ref_dict")
        section_item_to_update = self.form_section_items[item_index]
        logger.debug("section item before update = %s" % section_item_to_update)
        section_item_to_update[key] = gridfs_ref_dict
        logger.debug("section item after replacing file object with gridfs_ref_dict:")
        logger.debug("updated section item ( index %s) = %s" % (item_index, section_item_to_update))
        logger.debug("item updated OK")

        return filestorage.get_id(gridfs_ref_dict)

    def _delete_file(self, item_index, key):

        # This function deletes a file in gridfs in response to the user checking the "Clear" checkbox in
        # in the gui for a file cde.
        # The section item  containing this file cde was not deleted _itself_ though.
        # The mongo value for the file cde key needs to be set to None
        # and the file that _was_ referred to, deleted from gridfs.
        # We supply the existing nested data ( which is updated as a side effect
        # so that we can retrieve the original gridfs file id
        # and replace the old gridfs_ref_dict.

        logger.debug("file cde %s %s %s %s was cleared - deleting existing gridfs file" % (self.form_model.name,
                                                                                           self.multisection_code,
                                                                                           item_index,
                                                                                           key))
        file_cde_code = get_code(key)

        deleted_file_id = None

        for form_dict in self.existing_nested_data["forms"]:
            if form_dict["name"] == self.form_model.name:
                for section_dict in form_dict["sections"]:
                    if section_dict["code"] == self.multisection_code:
                        if section_dict["allow_multiple"]:
                            for index, item in enumerate(section_dict["cdes"]):
                                if index == item_index:
                                    for cde_dict in item:
                                        if cde_dict['code'] == file_cde_code:
                                            existing_gridfs_ref_dict = cde_dict["value"]
                                            logger.debug("existing cde value of this file cde = %s" %
                                                         existing_gridfs_ref_dict)
                                            deleted_file_id = self._delete_file_ref_dict(existing_gridfs_ref_dict)
                                            cde_dict["value"] = None
                                            logger.debug("updated the value to None")
        return deleted_file_id

    def _delete_file_ref_dict(self, file_ref):
        filestorage.delete_file_wrapper(self.gridfs_filestore, file_ref)

    def _get_original_file_cde_value(self, item_index, key):
        cde_code = get_code(key)
        old_index = self.index_map[item_index]
        for form_dict in self.original_data["forms"]:
            if form_dict["name"] == self.form_model.name:
                for section_dict in form_dict["sections"]:
                    if section_dict["code"] == self.multisection_code:
                        if section_dict["allow_multiple"]:
                            items = section_dict["cdes"]
                            old_cdes_list = items[old_index]
                            for cde_dict in old_cdes_list:
                                if cde_dict["code"] == cde_code:
                                    original_value = cde_dict["value"]
                                    return original_value

    def _preserve_file(self, item_index, key, original_value):
        cde_code = get_code(key)
        section_dict = self.form_section_items[item_index]
        section_dict[key] = original_value
        return filestorage.get_id(original_value)

    def _get_gridfs_fileids(self, items):
        result_set = set([])
        for cde_dict_list in items:
            for cde_dict in cde_dict_list:
                file_id = filestorage.get_id(cde_dict["value"])
                if file_id is not None:
                    result_set.add(file_id)

        return result_set

    # public

    def update_multisection_file_cdes(self):

        if self.index_map is None:
            # FH-28: Family Linkage ops cause the value of index or relative on a clinical form to be
            # changed - this change saves dynamic data without initialising index_map which causes
            # a runtime error, hence the bailout here
            return

        logger.debug("****************** START UPDATE MULTISECTION FILE CDES ****************************")
        logger.debug("updating any gridfs files in multisection %s" % self.multisection_code)

        try:
            existing_sections = self._get_existing_multisection_items()
        except KeyValueMissing:
            existing_sections = []

        existing_gridfs_ids_set = self._get_gridfs_fileids(existing_sections)  # gridfs fileids in existing multisection

        unchanged_gridfs_file_ids = set([])

        uploaded_files_to_add_to_gridfs = []
        unchanged_files = []
        files_to_delete = []

        for item_index, section_item_dict in enumerate(self.form_section_items):
            logger.debug("checking new saved section %s" % item_index)

            for key, value in section_item_dict.items():
                logger.debug("multisection %s item key = %s value = %s" % (item_index, key, value))
                if is_file_cde(get_code(key)):
                    logger.debug("%s is a file" % key)
                    if is_uploaded_file(value):
                        uploaded_files_to_add_to_gridfs.append((item_index, key, value))
                    elif value is None:
                        logger.debug("value is None - file unchanged")
                        unchanged_files.append((item_index, key))
                    elif value is False:
                        # indicates use wants to clear the file?
                        logger.debug("%s value is False - should delete this file")
                        files_to_delete.append((item_index, key))

        for item_index, key, file_object in uploaded_files_to_add_to_gridfs:
            added_gridfs_file_id = self._add_file(item_index, key, file_object)

            if not added_gridfs_file_id is None:
                self.added_file_ids.add(added_gridfs_file_id)

        for (item_index, key) in files_to_delete:
            deleted_gridfs_file_id = self._delete_file(item_index, key)
            if not deleted_gridfs_file_id is None:
                self.deleted_file_ids.add(deleted_gridfs_file_id)

        for (item_index, key) in unchanged_files:
            #todo ensure that unchanged gridfs files in a multisection are not clobbered
            original_value = self._get_original_file_cde_value(item_index, key)
            original_file_id = self._preserve_file(item_index, key, original_value)
            if original_file_id is not None:
                self.unchanged_file_ids.add(original_file_id)


        logger.debug("****************** END UPDATE MULTISECTION FILE CDES ****************************")

    def _get_existing_multisection_items(self):
        for form_dict in self.existing_nested_data["forms"]:
            if form_dict["name"] == self.form_model.name:
                for section_dict in form_dict["sections"]:
                    if section_dict["code"] == self.multisection_code:
                        if section_dict["allow_multiple"]:
                            # a list of cde dict lists ( code value dicts)
                            return section_dict['cdes']

        raise KeyValueMissing()


class FormDataParser(object):
    def __init__(self,
                 registry_model,
                 form_model,
                 form_data,
                 existing_record=None,
                 is_multisection=False,
                 parse_all_forms=False):
        self.registry_model = registry_model
        self.form_data = form_data
        self.parsed_data = {}
        self.parsed_multisections = {}
        self.global_timestamp = None
        self.form_timestamps = {}
        self.django_id = None
        self.django_model = None
        self.mongo_id = None
        self.existing_record = existing_record
        self.is_multisection = is_multisection
        self.form_model = form_model
        self.custom_consents = None
        self.address_data = None
        self.parse_all_forms = parse_all_forms

    def update_timestamps(self, form_model):
        t = datetime.now()
        form_timestamp = form_model.name + "_timestamp"
        self.global_timestamp = t
        self.form_timestamps[form_timestamp] = t

    def set_django_instance(self, instance):
        self.django_id = instance.pk
        self.django_model = instance.__class__.__name__

    @property
    def nested_data(self):
        if not self.parse_all_forms:
            self._parse()
        else:
            self._parse_all_forms()

        if self.existing_record:
            d = self.existing_record
        else:
            d = {"forms": []}

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
        logger.debug("parsing form value: %s" % value)
        if isinstance(value, FileUpload):
            logger.debug("FileUpload wrapper - returning the gridfs dict!")
            return value.mongo_data
        elif isinstance(value, InMemoryUploadedFile):
            logger.debug("InMemoryUploadedFile returning None")
            return None
        else:
            logger.debug("returning the bare value")
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
        self.testing = False
        self.obj = obj
        self.django_id = obj.pk
        self.django_model = obj.__class__
        # We inject these to allow unit testing
        self.client = None
        self.filestore_class = filestore_class
        # when saving data to Mongo this field allows timestamp to be recorded
        self.current_form_model = None
        self.rdrf_context_id = rdrf_context_id

        # holds reference to the complete data record for this object
        self.patient_record = None

    def _set_client(self):
        if self.client is None:
            self.client = construct_mongo_client()



    def __unicode__(self):
        return "Dynamic Data Wrapper for %s id=%s" % self.obj.__class__.__name__, self.obj.pk

    def _get_record_query(self, filter_by_context=True):
        django_model = self.obj.__class__.__name__
        django_id = self.obj.pk
        if filter_by_context:
            return {"django_model": django_model,
                    "django_id": django_id,
                    "context_id": self.rdrf_context_id}
        else:
            return {"django_model": django_model,
                    "django_id": django_id}

    def _get_collection(self, registry, collection_name, add_mongo_prefix=True):
        if not self.testing:
            if add_mongo_prefix:
                db_name = mongo_db_name(registry)
            else:
                db_name = registry
            db = self.client[db_name]
        else:
            db = self.client["testing_" + registry]

        collection = db[collection_name]
        return collection

    def get_filestore(self, registry):
        self._set_client()
        if not self.testing:
            db = self.client[mongo_db_name(registry)]
        else:
            db = self.client["testing_" + registry]

        if self.filestore_class is None:
            import gridfs
            cls = gridfs.GridFS
        else:
            cls = self.filestore_class

        return cls(db, collection=registry + ".files")

    def has_data(self, registry_code):
        data = self.load_dynamic_data(registry_code, "cdes")
        return data is not None

    def load_dynamic_data(self, registry, collection_name, flattened=True):
        """
        :param registry: e.g. sma or dmd
        :param collection_name: e.g. cde or hpo
        :param flattened: use flattened to get data in a form suitable for the view
        :return: a dictionary of nested or flattened data for this instance
        """
        self._set_client()
        record_query = self._get_record_query()
        collection = self._get_collection(registry, collection_name)
        nested_data = collection.find_one(record_query)
        if nested_data is None:
            return None

        if flattened:
            flattened_data = {}
            for k in nested_data:
                if k != "forms":
                    flattened_data[k] = nested_data[k]

            for form_dict in nested_data["forms"]:
                for section_dict in form_dict["sections"]:
                    if not section_dict["allow_multiple"]:
                        for cde_dict in section_dict["cdes"]:
                            value = cde_dict["value"]
                            delimited_key = mongo_key(form_dict["name"], section_dict["code"], cde_dict["code"])
                            flattened_data[delimited_key] = value
                    else:
                        multisection_code = section_dict["code"]
                        flattened_data[multisection_code] = []
                        multisection_items = section_dict["cdes"]
                        for cde_list in multisection_items:
                            d = {}
                            for cde_dict in cde_list:
                                cde_code = cde_dict["code"]
                                cde_value = cde_dict["value"]
                                delimited_key = mongo_key(form_dict["name"], section_dict["code"], cde_dict["code"])
                                d[delimited_key] = cde_value
                            flattened_data[multisection_code].append(d)

            return flattened_data
        else:
            return nested_data

    def get_cde_val(self, registry_code, form_name, section_code, cde_code):
        data = self.load_dynamic_data(registry_code, "cdes", flattened=False)
        return self._find_cde_val(data, registry_code, form_name, section_code, cde_code)

    @staticmethod
    def _find_cde_val(record, registry_code, form_name, section_code, cde_code):
        form_map = {f.get("name"): f for f in record.get("forms", [])}
        sections = form_map.get(form_name, {}).get("sections", [])
        section_map = {s.get("code"): s for s in sections}
        cdes = section_map.get(section_code, {}).get("cdes", [])
        cde_map = {c.get("code"): c for c in cdes}
        return cde_map.get(cde_code, {}).get("value")

    def get_cde_history(self, registry_code, form_name, section_code, cde_code):
        def fmt(snapshot):
            return {
                "timestamp": datetime.strptime(snapshot["timestamp"][:19], "%Y-%m-%d %H:%M:%S"),
                "value": self._find_cde_val(snapshot["record"], registry_code,
                                                     form_name, section_code,
                                                     cde_code),
                "id": str(snapshot["_id"]),
            }
        def collapse_same(snapshots):
            prev = { "": None }  # nonlocal works in python3
            def is_different(snap):
                diff = prev[""] is None or snap["value"] != prev[""]["value"]
                prev[""] = snap
                return diff
            return list(filter(is_different, snapshots))
        record_query = self._get_record_query(filter_by_context=False)
        record_query["record_type"] = "snapshot"
        collection = self._get_collection(registry_code, "history")
        data = map(fmt, collection.find(record_query))
        return collapse_same(sorted(data, key=itemgetter("timestamp")))

    def load_contexts(self, registry_model):
        self._set_client()
        logger.debug("registry model = %s" % registry_model)
        if not registry_model.has_feature("contexts"):
            raise Exception("Registry %s does not support use of contexts" % registry_model.code)

        logger.debug("registry supports contexts so retreiving")
        from rdrf.models import RDRFContext
        django_model = self.obj.__class__.__name__
        mongo_query = {"django_id": self.django_id,
                       "django_model": django_model }
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
        record_query = self._get_record_query()
        logger.debug("record_query = %s" % record_query)
        collection = self._get_collection(registry_model.code,
                                          self.REGISTRY_SPECIFIC_PATIENT_DATA_COLLECTION)
        registry_data = collection.find_one(record_query)
        if registry_data:
            for k in ['django_id', '_id', 'django_model']:
                    del registry_data[k]
            data[registry_model.code] = registry_data

        for registry_code in data:
            self._wrap_gridfs_files_from_mongo(registry_model, data[registry_code])
        logger.debug("registry_specific_data after wrapping for files = %s" % data)
        return data

    def _get_registry_codes(self):
        reg_codes = self.client.database_names()
        return reg_codes

    def save_registry_specific_data(self, data):
        self._set_client()
        logger.debug("saving registry specific mongo data: %s" % data)
        for reg_code in data:
            registry_data = data[reg_code]
            if not registry_data:
                continue
            collection = self._get_collection(reg_code, "registry_specific_patient_data")
            query = self._get_record_query()
            record = collection.find_one(query)
            if record:
                mongo_id = record['_id']
                collection.update({'_id': mongo_id}, {"$set": registry_data}, upsert=False)
            else:
                record = self._get_record_query()
                record.update(registry_data)
                collection.insert(record)

    def _wrap_gridfs_files_from_mongo(self, registry, data):
        """
        :param data: Dynamic data loaded from Mongo
        :return: --  nothing Munges the passed in dictionary to display FileUpload wrappers
        """

        if data is None:
            return
        if isinstance(data, unicode):
            return

        if isinstance(data, list):
            for thing in data:
                self._wrap_gridfs_files_from_mongo(registry, thing)
            return

        for key, value in data.items():
            if filestorage.get_id(value) is not None:
                wrapper = FileUpload(registry, key, value)
                data[key] = wrapper

            elif isinstance(value, list):
                # section data
                for section_dict in value:
                    self._wrap_gridfs_files_from_mongo(registry, section_dict)

    def _store_file(
            self,
            registry,
            patient_record,
            cde_code,
            in_memory_file,
            dynamic_data):
        logger.debug("storing file for key %s" % cde_code)
        dynamic_data[cde_code] = filestorage.store_file_by_key(
            registry, patient_record, cde_code, in_memory_file)

    def _is_section_code(self, code):
        # Supplied code will be non-delimited
        from models import Section
        return Section.objects.filter(code=code).exists()

    def _update_files_in_gridfs(self, existing_record, registry, new_data, index_map):

        fs = self.get_filestore(registry)

        def get_mongo_value(registry_code, nested_data, delimited_key):
            from rdrf.utils import models_from_mongo_key
            from rdrf.models import Registry
            registry_model = Registry.objects.get(code=registry_code)

            form_model, section_model, cde_model = models_from_mongo_key(registry_model, delimited_key)

            for form_dict in nested_data["forms"]:
                if form_dict["name"] == form_model.name:
                    for section_dict in form_dict["sections"]:
                        if section_dict["code"] == section_model.code:
                            if not section_dict["allow_multiple"]:
                                for cde_dict in section_dict['cdes']:
                                    if cde_dict["code"] == cde_model.code:
                                        return cde_dict["value"]
            raise KeyValueMissing()

        logger.debug("_update_files_in_gridfs: existing record = %s new_data = %s" % (existing_record, new_data))

        for key, value in new_data.items():

            if is_file_cde(get_code(key)):
                logger.debug("updating file reference for cde %s" % key)
                delete_existing = True
                logger.debug("uploaded file value: %s" % value)

                if value is False:
                    logger.debug("User cleared %s - file will be deleted" % key)
                    # Django uses a "clear" checkbox value of False to indicate file should be removed
                    # we need to delete the file but not here
                    continue

                if value is None:
                    logger.debug(
                        "User did not change file %s - existing_record will not be updated" % key)
                    logger.debug("existing_record = %s\nnew_data = %s" %
                                 (existing_record, new_data))
                    delete_existing = False

                try:
                    existing_value = get_mongo_value(registry, existing_record, key)
                    in_mongo = True
                except KeyValueMissing, err:
                    in_mongo = False
                    existing_value = None

                if in_mongo:
                    logger.debug("key %s in existing record - value is file wrapper" % key)
                    file_wrapper = existing_value
                    logger.debug("file_wrapper = %s" % file_wrapper)
                else:
                    file_wrapper = None
                    logger.debug("key %s is not in existing record - setting file_wrapper to None" % key)

                if isinstance(file_wrapper, InMemoryUploadedFile):
                    logger.debug("file_wrapper is an InMemoryUploadedFile -setting to None?")
                    file_wrapper = None

                logger.debug("File wrapper = %s" % file_wrapper)

                if not file_wrapper:
                    logger.debug("file_wrapper None so checking incoming value from form")
                    if value is not None:
                        logger.debug("new value is not None: %s" % value)
                        logger.debug("storing file for cde %s value = %s" % (key, value))
                        self._store_file(
                            registry, existing_record, key, value, new_data)
                    else:
                        logger.debug("incoming value is None so no update")
                else:
                    logger.debug("existing value is a file wrapper: %s" % file_wrapper)
                    if isinstance(file_wrapper, FileUpload):
                        gridfs_file_dict = file_wrapper.gridfs_dict
                    elif filestorage.get_id(file_wrapper):
                        gridfs_file_dict = file_wrapper
                    logger.debug("existing gridfs dict = %s" % gridfs_file_dict)

                    if gridfs_file_dict is None:
                        if value is not None:
                            logger.debug("storing file with value %s in gridfs" % value)
                            self._store_file(
                                registry, existing_record, key, value, new_data)
                    else:
                        if delete_existing:
                            logger.debug("delete_existing is True so trying to delete the file originally stored")
                            logger.debug(
                                "updated value is not None so we delete existing upload and update:")
                            filestorage.delete_file_wrapper(fs, file_wrapper)
                            if value is not None:
                                logger.debug("updating %s -> %s" % (key, value))
                                logger.debug("storing updated file data in gridfs")
                                self._store_file(
                                    registry, existing_record, key, value, new_data)
                        else:
                            # don't change anything on update ...
                            logger.debug("delete_existing is False - just replacing the gridfs_file_dict")
                            new_data[key] = gridfs_file_dict
                            logger.debug("new_data[%s]  is now %s" % (key, gridfs_file_dict))

            elif self._is_section_code(key):

                new_section_items = value
                if self.current_form_model:
                    form_model = self.current_form_model
                else:
                    #todo fix this
                    form_model = None

                if form_model is None:
                    return

                multisection_gridfs_handler = MultisectionGridFSFileHandler(fs,
                                                                            registry,
                                                                            form_model,
                                                                            key,
                                                                            new_section_items,
                                                                            existing_record,
                                                                            index_map)

                multisection_gridfs_handler.update_multisection_file_cdes()

    def _update_file_cde(self, section_index, key, value, existing_record):
        logger.debug("updating file reference for cde %s" % key)
        delete_existing = True
        logger.debug("uploaded file value: %s" % value)

        if value is False:
            logger.debug("User cleared %s - file will be deleted" % key)
            # Django uses a "clear" checkbox value of False to indicate file should be removed
            # we need to delete the file but not here
            return

        if value is None:
            logger.debug(
                "User did not change file %s - existing_record will not be updated" % key)
            logger.debug("existing_record = %s\nnew_data = %s" %
                         (existing_record, new_data))
            delete_existing = False

        try:
            existing_value = get_mongo_value(registry, existing_record, key)
            in_mongo = True
        except KeyValueMissing, err:
            in_mongo = False
            existing_value = None

        if in_mongo:
            logger.debug("key %s in existing record - value is file wrapper" % key)
            file_wrapper = existing_value
            logger.debug("file_wrapper = %s" % file_wrapper)
        else:
            file_wrapper = None
            logger.debug("key %s is not in existing record - setting file_wrapper to None" % key)

        if isinstance(file_wrapper, InMemoryUploadedFile):
            logger.debug("file_wrapper is an InMemoryUploadedFile -setting to None?")
            file_wrapper = None

        logger.debug("File wrapper = %s" % file_wrapper)

        if not file_wrapper:
            logger.debug("file_wrapper None so checking incoming value from form")
            if value is not None:
                logger.debug("new value is not None: %s" % value)
                logger.debug("storing file for cde %s value = %s" % (key, value))
                self._store_file(
                    registry, existing_record, key, value, new_data)
            else:
                logger.debug("incoming value is None so no update")
        else:
            logger.debug("existing value is a file wrapper: %s" % file_wrapper)
            if isinstance(file_wrapper, FileUpload):
                gridfs_file_dict = file_wrapper.gridfs_dict
            elif filestorage.get_id(file_wrapper) is not None:
                gridfs_file_dict = file_wrapper
            logger.debug("existing gridfs dict = %s" % gridfs_file_dict)

            if gridfs_file_dict is None:
                if value is not None:
                    logger.debug("storing file with value %s in gridfs" % value)
                    self._store_file(
                        registry, existing_record, key, value, new_data)
            else:
                logger.debug("checking file id on existing gridfs dict")
                if delete_existing:
                    # fixme: fs not defined
                    filestorage.delete_file_wrapper(fs, gridfs_file_dict)
                    if value is not None:
                        logger.debug("updating %s -> %s" % (key, value))
                        logger.debug("storing updated file data in gridfs")
                        self._store_file(
                            registry, existing_record, key, value, new_data)
                else:
                    # don't change anything on update ...
                    logger.debug("delete_existing is False - just replacing the gridfs_file_dict")
                    new_data[key] = gridfs_file_dict
                    logger.debug("new_data[%s]  is now %s" % (key, gridfs_file_dict))


    def _get_form_model_from_section_data(self, registry_code, multisection_cde_dict):
        delimited_keys = [ key for key in multisection_cde_dict.keys() if is_delimited_key(key)]
        if len(delimited_keys) > 0:
            delimited_key = delimited_keys[0]
            form_name = delimited_key.split("____")[0]
            try:
                from rdrf.models import RegistryForm
                form_model = RegistryForm.objects.get(name=form_name, registry=registry_model)
                return form_model
            except RegistryForm.DoesNotExist:
                return None

        return None


    def update_dynamic_data(self, registry_model, mongo_record):
        logger.info("About to update %s in %s with new mongo_record %s" % (self.obj,
                                                                           registry_model,
                                                                           mongo_record))
        self._set_client()
        # replace entire mongo record with supplied one
        # assumes structure correct ..
        collection = self._get_collection(registry_model.code, "cdes")
        if "_id" in mongo_record:
            mongo_id = mongo_record["_id"]
            logger.info("updating monfgo record for object id %s" % mongo_id)
            logger.info("record to update = %s" % mongo_record)
            collection.update({'_id': mongo_id}, {"$set": mongo_record}, upsert=False)
            logger.info("updated ok")
        else:
            logger.info("no object id in record will insert")
            collection.insert(mongo_record)
            logger.info("inserted ok")

    def delete_patient_record(self, registry_model, context_id):
        self._set_client()
        self.rdrf_context_id = context_id
        logger.info("delete_patient_record called: patient %s registry %s context %s" % (self.obj,
                                                                registry_model,
                                                                context_id))

        # used _only_ when trying to emulate a roll-back to no data after an exception  in questionnaire handling
        if self.obj.__class__.__name__ != 'Patient':
            raise Exception("can't delete non-patient record")

        patient_model = self.obj


        collection = self._get_collection(registry_model.code, "cdes")
        logger.debug("collection = %s" % collection)
        
        filter = {"django_id": self.obj.pk,
                 "django_model": 'Patient',
                 "context_id": context_id}

        logger.info("Deleting patient record from mongo for rollback: %s" % filter)
        try:
            collection.remove(filter)
            logger.info("deleted OK..")
        except Exception, ex:
            logger.error("Error deleting record: %s" % ex)
            
        
        
        
        


    def save_dynamic_data(self, registry, collection_name, form_data, multisection=False, parse_all_forms=False,
                          index_map=None):
        from rdrf.models import Registry
        self._set_client()
        self._convert_date_to_datetime(form_data)
        collection = self._get_collection(registry, collection_name)

        existing_record = self.load_dynamic_data(registry, collection_name, flattened=False)

        form_data["timestamp"] = datetime.now()

        if self.current_form_model:
            form_timestamp_key = "%s_timestamp" % self.current_form_model.name
            form_data[form_timestamp_key] = form_data["timestamp"]

        if existing_record:
            logger.debug("saving dynamic data - updating existing")
            mongo_id = existing_record['_id']
            self._update_files_in_gridfs(existing_record, registry, form_data, index_map)
            logger.debug("after update: %s" % form_data)

            form_data_parser = FormDataParser(Registry.objects.get(code=registry),
                                              self.current_form_model,
                                              form_data,
                                              existing_record=existing_record,
                                              is_multisection=multisection,
                                              parse_all_forms=parse_all_forms)

            form_data_parser.set_django_instance(self.obj)

            if self.current_form_model:
                form_data_parser.form_name = self.current_form_model

            nested_data = form_data_parser.nested_data
            logger.debug("nested data = %s" % nested_data)

            collection.update({'_id': mongo_id}, {"$set": form_data_parser.nested_data}, upsert=False)
        else:
            record = self._get_record_query()
            record["forms"] = []
            self._update_files_in_gridfs(record, registry, form_data, index_map)

            form_data_parser = FormDataParser(Registry.objects.get(code=registry),
                                              self.current_form_model,
                                              form_data,
                                              existing_record=record,
                                              is_multisection=multisection,
                                              parse_all_forms=parse_all_forms)

            form_data_parser.set_django_instance(self.obj)

            if self.current_form_model:
                form_data_parser.form_name = self.current_form_model

            nested_data = form_data_parser.nested_data

            logger.debug("nested data to insert = %s" % nested_data)

            collection.insert(form_data_parser.nested_data)

    def _save_longitudinal_snapshot(self, registry_code, record):
        try:
            timestamp = str(datetime.now())
            patient_id = record['django_id']
            history = self._get_collection(registry_code, "history")
            snapshot = {"django_id": patient_id,
                        "django_model": record.get("django_model", None),
                        "registry_code": registry_code,
                        "record_type": "snapshot",
                        "timestamp": timestamp,
                        "record": record,
                        }
            history.insert(snapshot)
            logger.debug("snapshot added for %s patient %s timestamp %s" % (registry_code, patient_id, timestamp))

        except Exception as ex:
            logger.error("Couldn't add to history for patient %s: %s" % (patient_id, ex))

    def save_snapshot(self, registry_code, collection_name):
        try:
            record = self.load_dynamic_data(registry_code, collection_name, flattened=False)
            self._save_longitudinal_snapshot(registry_code, record)
        except Exception as ex:
            logger.error("Error saving longitudinal snapshot: %s" % ex)

    def save_form_progress(self, registry_code, context_model=None):
        from rdrf.form_progress import FormProgress
        from rdrf.models import Registry
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
        from datetime import date
        from datetime import datetime

        if isinstance(data, unicode):
            return

        if isinstance(data, list):
            for x in data:
                self._convert_date_to_datetime(x)

        for k, value in data.items():
            if isinstance(value, date):
                data[k] = datetime(value.year, value.month, value.day)
            elif isinstance(value, list):
                # recurse on multisection data
                for e in value:
                    self._convert_date_to_datetime(e)

    def _set_in_memory_uploaded_files_to_none(self, data):
        logger.debug("setting uploaded files to None for data = %s" % data)
        if not isinstance(data, dict):
            # TODO find a better way! this test added to fix RDR-634
            # The items in a multiple allowed select widget were being passed in here
            # ( values in the list are not dicts so the recursive call failed below)
            return
        keys_to_change = []
        for key, value in data.items():
            if isinstance(value, InMemoryUploadedFile):
                keys_to_change.append(key)
                logger.debug("setting key %s InMemoryUploadedFile to None: " % key)
            elif isinstance(value, list):
                for item in value:
                    self._set_in_memory_uploaded_files_to_none(item)
        for key in keys_to_change:
            data[key] = None

    def delete_patient_data(self, registry_model, patient_model):
        cdes = self._get_collection(registry_model, "cdes")
        cdes.remove({"django_id": patient_model.pk, "django_model": "Patient"})

    def get_cde(self, registry, section, cde_code):
        if not self.testing:
            db = self.client[mongo_db_name(registry)]
        else:
            db = self.client["testing_" + registry]

        collection = db["cdes"]
        cde_mongo_key = "%s____%s____%s" % (registry.upper(), section, cde_code)
        cde_record = collection.find_one(self._get_record_query(), {cde_mongo_key: True})
        cde_value = self._get_value_from_cde_record(cde_mongo_key, cde_record)

        return cde_value

    def get_nested_cde(self, registry_code, form_name, section_code, cde_code):

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

    def _get_value_from_cde_record(self, cde_mongo_key, cde_record):
        try:
            return cde_record[cde_mongo_key]
        except KeyError:
            return None

    def get_form_timestamp(self, registry_form):
        if not self.testing:
            db = self.client[mongo_db_name(registry_form.registry.code)]
        else:
            db = self.client["testing_" + registry_form.registry.code]

        collection = db["cdes"]
        form_timestamp = collection.find_one(self._get_record_query(), {"timestamp": True})

        return form_timestamp
