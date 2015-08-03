from django.core.files.uploadedfile import InMemoryUploadedFile
from pymongo import MongoClient
import gridfs
import logging
from rdrf.utils import get_code, mongo_db_name, models_from_mongo_key, is_delimited_key, mongo_key, is_multisection
from django.conf import settings
import datetime

logger = logging.getLogger("registry_log")


class FileStore(object):

    def __init__(self, mongo_db):
        self.fs = gridfs.GridFS(mongo_db)


class FormParsingError(Exception):
    pass


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
        from datetime import datetime
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
                if self._is_file(value):
                    value = self._get_gridfs_value(value)
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
                self.parsed_data[(form_model, section_model, cde_model)] = value

    def _parse_multisection(self, multisection_code):
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
                    cde_dict = {"code": cde_model.code, "value": value}
                    item.append(cde_dict)
            items.append(item)
        self.parsed_multisections[(the_form_model, the_section_model)] = items

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
                    self.parsed_data[(form_model, section_model, cde_model)] = value
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
            client=MongoClient(
                settings.MONGOSERVER,
                settings.MONGOPORT),
            filestore_class=gridfs.GridFS):
        # When set to True by integration tests, uses testing mongo database
        self.testing = False
        self.obj = obj
        self.django_id = obj.pk
        self.django_model = obj.__class__
        # We inject these to allow unit testing
        self.client = client
        self.file_store_class = filestore_class
        # when saving data to Mongo this field allows timestamp to be recorded
        self.current_form_model = None

        # holds reference to the complete data record for this object
        self.patient_record = None

    def __unicode__(self):
        return "Dynamic Data Wrapper for %s id=%s" % self.obj.__class__.__name__, self.obj.pk

    def _get_record_query(self):
        django_model = self.obj.__class__.__name__
        django_id = self.obj.pk
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

    def _get_filestore(self, registry):
        if not self.testing:
            db = self.client[mongo_db_name(registry)]
        else:
            db = self.client["testing_" + registry]

        return self.file_store_class(db, collection=registry + ".files")

    def load_dynamic_data(self, registry, collection_name, flattened=True):
        """
        :param registry: e.g. sma or dmd
        :param collection_name: e.g. cde or hpo
        :param flattened: use flattened to get data in a form suitable for the view
        :return: a dictionary of nested or flattened data for this instance
        """
        record_query = self._get_record_query()
        collection = self._get_collection(registry, collection_name)
        nested_data = collection.find_one(record_query)
        logger.debug("load_dynamic_data : nested_data is: %s" % nested_data)
        if nested_data is None:
            logger.debug("loading dynamic data - nested data is None so returning None")
            return None

        self._wrap_gridfs_files_from_mongo(registry, nested_data)
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

    def load_registry_specific_data(self):
        data = {}
        record_query = self._get_record_query()
        logger.debug("record_query = %s" % record_query)
        for reg_code in self._get_registry_codes():
            # NB. We DON'T need to add Mongo prefix here as we've retrieved the actual
            # ( already prefixed db names from Mongo
            collection = self._get_collection(
                reg_code,
                self.REGISTRY_SPECIFIC_PATIENT_DATA_COLLECTION,
                add_mongo_prefix=False)
            registry_data = collection.find_one(record_query)
            if registry_data:
                for k in ['django_id', '_id', 'django_model']:
                    del registry_data[k]
                data[reg_code] = registry_data

        logger.debug("registry_specific_data  = %s" % data)
        return data

    def _get_registry_codes(self):
        reg_codes = self.client.database_names()
        return reg_codes

    def save_registry_specific_data(self, data):
        logger.debug("saving registry specific mongo data: %s" % data)
        for reg_code in data:
            registry_data = data[reg_code]
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
        :return: --  nothing Munges the passed in dictionary

        """
        if data is None:
            return
        if isinstance(data, unicode):
            return

        for key, value in data.items():
            if isinstance(value, dict):
                if "gridfs_file_id" in value:
                    class FileUpload(object):

                        def __init__(self, registry, cde_code, gridfs_dict):
                            self.cde_code = cde_code
                            self.gridfs_dict = gridfs_dict
                            from django.core.urlresolvers import reverse
                            self.url = reverse(
                                "file_upload", args=[
                                    registry, str(
                                        self.gridfs_dict['gridfs_file_id'])])

                        def __unicode__(self):
                            """
                            This is to satisfy Django's ClearableFileInputWidget which
                            uses django's force_text function
                            """
                            return self.gridfs_dict['file_name']

                    wrapper = FileUpload(registry, key, value)
                    data[key] = wrapper

            elif isinstance(value, list):
                # section data
                for section_dict in value:
                    self._wrap_gridfs_files_from_mongo(registry, section_dict)

    def _get_gridfs_filename(self, registry, data_record, cde_code, original_file_name):
        return "%s****%s****%s****%s****%s" % (registry,
                                               self.django_model,
                                               self.django_id,
                                               cde_code,
                                               original_file_name)

    def _store_file_in_gridfs(
            self,
            registry,
            patient_record,
            cde_code,
            in_memory_file,
            dynamic_data):
        logger.debug("storing file in gridfs")
        logger.debug("dynamic data supplied = %s" % dynamic_data)
        fs = self._get_filestore(registry)
        original_file_name = in_memory_file.name
        logger.debug("original filename = %s" % original_file_name)

        file_name = self._get_gridfs_filename(
            registry, patient_record, cde_code, original_file_name)

        logger.debug("gridfs filename = %s" % file_name)
        gridfs_id = fs.put(in_memory_file.read(), filename=file_name)
        logger.debug("gridfs_id = %s" % gridfs_id)
        # _alter_ the dyamic data to store reference to gridfs + the original file name

        grid_ref_dict = {"gridfs_file_id": gridfs_id, "file_name": in_memory_file.name}

        logger.debug("grid_ref_dict = %s" % grid_ref_dict)

        dynamic_data[cde_code] = grid_ref_dict
        logger.debug(
            "UPLOADED FILE %s = %s into registry %s as %s ( dict = %s )" %
            (cde_code,
             original_file_name,
             registry,
             gridfs_id,
             dynamic_data[cde_code]))
        return gridfs_id

    def _is_file_cde(self, code):
        from models import CommonDataElement
        try:
            cde = CommonDataElement.objects.get(code=code)
            if cde.datatype == 'file':
                logger.debug("CDE %s is a file!" % cde.code)
                return True
        except Exception as ex:
            # section forms have codes which are not CDEs
            return False

    def _is_section_code(self, code):
        # Supplied code will be non-delimited
        from models import Section
        try:
            Section.objects.get(code=code)
            return True
        except:
            pass
        return False

    def _update_files_in_gridfs(self, existing_record, registry, new_data):
        fs = self._get_filestore(registry)
        for key, value in new_data.items():
            if self._is_file_cde(get_code(key)):
                logger.debug("updating file reference for cde %s" % key)
                delete_existing = True
                logger.debug("uploaded file: %s" % key)



                if value is False:
                    logger.debug("User cleared %s - file will be deleted" % key)
                    # Django uses a "clear" checkbox value of False to indicate file should be removed
                    # we need to delete the file but not here
                    continue

                if value is None:
                    logger.debug(
                        "User did change file %s - existing_record will not be updated" % key)
                    logger.debug("existing_record = %s\nnew_data = %s" %
                                 (existing_record, new_data))
                    delete_existing = False

                if key in existing_record:
                    file_wrapper = existing_record[key]
                else:
                    file_wrapper = None

                if isinstance(file_wrapper, InMemoryUploadedFile):
                    file_wrapper = None

                logger.debug("File wrapper = %s" % file_wrapper)

                if not file_wrapper:
                    if value is not None:
                        logger.debug("storing file for cde %s value = %s" % (key, value))
                        self._store_file_in_gridfs(
                            registry, existing_record, key, value, new_data)
                    else:
                        logger.debug("did not update file as value is None")
                else:
                    gridfs_file_dict = file_wrapper.gridfs_dict
                    logger.debug("existing gridfs dict = %s" % gridfs_file_dict)

                    if gridfs_file_dict is None:
                        if value is not None:
                            logger.debug("storing file with value %s" % value)
                            self._store_file_in_gridfs(
                                registry, existing_record, key, value, new_data)
                    else:
                        logger.debug("checking file id on existing gridfs dict")
                        gridfs_file_id = gridfs_file_dict["gridfs_file_id"]
                        logger.debug("existing file id = %s" % gridfs_file_id)
                        if delete_existing:
                            logger.debug(
                                "updated value is not None so we delete existing upload and update:")
                            if fs.exists(gridfs_file_id):
                                fs.delete(gridfs_file_id)
                                logger.debug("deleted existing file with id %s" %
                                             gridfs_file_id)
                            else:
                                logger.debug(
                                    "file id %s in existing_record didn't exist?" %
                                    gridfs_file_id)
                            if value is not None:
                                logger.debug("updating %s -> %s" % (key, value))
                                self._store_file_in_gridfs(
                                    registry, existing_record, key, value, new_data)
                        else:
                            # don't change anything on update ...
                            new_data[key] = gridfs_file_dict

            elif self._is_section_code(key):
                # value is a list of section field data dictionaries
                if key not in existing_record:
                    existing_record[key] = [{}] * len(value)
                elif len(existing_record[key]) < len(value):
                    num_extra_dicts = len(value) - len(existing_record[key])
                    existing_record[key].extend([{}] * num_extra_dicts)

                for i, section_data_dict in enumerate(value):
                    existing_section_dict = existing_record[key][i]
                    self._update_files_in_gridfs(
                        existing_section_dict, registry, section_data_dict)

    def save_dynamic_data(self, registry, collection_name, form_data, multisection=False, parse_all_forms=False):
        from rdrf.models import Registry
        self._convert_date_to_datetime(form_data)
        collection = self._get_collection(registry, collection_name)

        existing_record = self.load_dynamic_data(registry, collection_name, flattened=False)

        form_data["timestamp"] = datetime.datetime.now()

        if self.current_form_model:
            form_timestamp_key = "%s_timestamp" % self.current_form_model.name
            form_data[form_timestamp_key] = form_data["timestamp"]

        if existing_record:
            mongo_id = existing_record['_id']
            logger.debug("************  updating gridfs ****************************")
            self._update_files_in_gridfs(existing_record, registry, form_data)
            logger.debug("after update: %s" %  form_data)

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
            record.update(form_data)
            self._set_in_memory_uploaded_files_to_none(record)
            self._update_files_in_gridfs(record, registry, form_data)

            form_data_parser = FormDataParser(Registry.objects.get(code=registry),
                                              self.current_form_model,
                                              record,
                                              is_multisection=multisection,
                                              parse_all_forms=parse_all_forms)

            form_data_parser.set_django_instance(self.obj)

            if self.current_form_model:
                form_data_parser.form_name = self.current_form_model

            nested_data = form_data_parser.nested_data

            logger.debug("nested data to insert = %s" % nested_data)

            collection.insert(form_data_parser.nested_data)

    def _save_longitudinal_snapshot(self, registry, record):
        try:
            from datetime import datetime
            timestamp = str(datetime.now())
            patient_id = record['django_id']
            history = self._get_collection(registry, "history")
            h = history.find_one({"_id": patient_id})
            if h is None:
                history.insert({"_id": patient_id, "snapshots": []})
            history.update(
                {"_id": patient_id}, {"$push": {"snapshots": {"timestamp": timestamp, "record": record}}})
        except Exception as ex:
            logger.error("Couldn't add to history for patient %s: %s" % (patient_id, ex))

    def save_snapshot(self, registry_code, collection_name):
        try:
            record = self.load_dynamic_data(registry_code, collection_name)
            self._save_longitudinal_snapshot(registry_code, record)
        except Exception as ex:
            logger.error("Error saving longitudinal snapshot: %s" % ex)

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
        logger.debug("dynamic data = %s" % data)
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


