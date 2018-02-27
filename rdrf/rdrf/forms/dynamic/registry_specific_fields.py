from collections import OrderedDict
from rdrf.db.dynamic_data import DynamicDataWrapper
from django.utils.datastructures import MultiValueDictKeyError
from rdrf.helpers.utils import is_uploaded_file
from rdrf.db import filestorage

import logging
logger = logging.getLogger(__name__)


class FileCommand:
    DELETE = "DELETE"
    PRESERVE = "PRESERVE"
    UPLOAD = "UPLOAD"


class RegistrySpecificFieldsHandler(object):

    def __init__(self, registry_model, patient_model):
        self.registry_model = registry_model
        self.patient_model = patient_model
        self.mongo_wrapper = DynamicDataWrapper(self.patient_model)

    def save_registry_specific_data_in_mongo(self, request):
        if self.registry_model.patient_fields and self.allowed_to_write_data():
            mongo_patient_data = {self.registry_model.code: {}}
            for cde_model, field_object in self.registry_model.patient_fields:
                if not cde_model.datatype == "file":
                    try:
                        field_value = request.POST[cde_model.code]
                        mongo_patient_data[self.registry_model.code][cde_model.code] = field_value
                    except MultiValueDictKeyError:
                        continue
                else:
                    form_value = self._get_file_form_value(cde_model, request)
                    if form_value == FileCommand.PRESERVE:
                        # preserve existing value
                        existing_data = self.get_registry_specific_data()
                        if existing_data and self.registry_model.code in existing_data:
                            data = existing_data[self.registry_model.code][cde_model.code]
                            if data:
                                form_value = data
                            else:
                                form_value = {}
                        else:
                            form_value = {}

                    elif form_value == FileCommand.DELETE:
                        form_value = {}

                    processed_value = self._process_file_cde_value(cde_model, form_value)
                    mongo_patient_data[self.registry_model.code][cde_model.code] = processed_value

            self.mongo_wrapper.save_registry_specific_data(mongo_patient_data)

    def allowed_to_write_data(self):
        if self.registry_model.has_feature("family_linkage"):
            return self.patient_model.is_index
        else:
            return True

    def _delete_existing_file_in_fs(self, file_cde_model):
        existing_data = self.get_registry_specific_data()
        file_upload_wrapper = existing_data[self.registry_model.code][file_cde_model.code]
        filestorage.delete_file_wrapper(file_upload_wrapper)

    def _process_file_cde_value(self, file_cde_model, form_value):
        if is_uploaded_file(form_value):
            return filestorage.store_file(
                self.registry_model.code,
                file_cde_model.code, form_value,
                form_name="reg_spec",
                section_code="reg_spec")
        else:
            return form_value

    def _get_file_form_value(self, file_cde_model, request):
        clear_key = file_cde_model.code + "-clear"
        if file_cde_model.code in request.FILES:
            in_memory_uploaded_file = request.FILES[file_cde_model.code]
            return in_memory_uploaded_file

        elif clear_key in request.POST:
            clear_value = request.POST[clear_key]
            if clear_value == "on":
                return FileCommand.DELETE

        elif file_cde_model.code in request.POST:
            posted_value = request.POST[file_cde_model.code]
            if posted_value == "":
                return FileCommand.PRESERVE
            return posted_value

        else:
            raise Exception("file cde not found")

    def get_registry_specific_fields(self, user):
        if user.is_superuser:
            fields = self.registry_model.patient_fields
            return fields

        if self.registry_model not in user.registry.all():
            return []
        else:
            return self.registry_model.patient_fields

    def create_registry_specific_patient_form_class(self, user, form_class):
        additional_fields = OrderedDict()
        field_pairs = self.get_registry_specific_fields(user)
        if not field_pairs:
            return form_class

        for cde, field_object in field_pairs:
            additional_fields[cde.code] = field_object

        new_form_class = type(form_class.__name__, (form_class,), additional_fields)
        return new_form_class

    def get_registry_specific_section_fields(self, user):
        field_pairs = self.get_registry_specific_fields(user)
        fieldset_title = self.registry_model.specific_fields_section_title
        field_list = [pair[0].code for pair in field_pairs]
        return fieldset_title, field_list

    # loading
    def get_registry_specific_data(self):
        if self.patient_model is None:
            return {}
        data = self.mongo_wrapper.load_registry_specific_data(self.registry_model)
        return data
