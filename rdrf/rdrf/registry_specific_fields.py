from rdrf.dynamic_data import DynamicDataWrapper
from django.utils.datastructures import MultiValueDictKeyError
from rdrf.utils import is_uploaded_file
from rdrf.file_upload import FileUpload, wrap_gridfs_data_for_form
from rdrf.filestorage import GridFSApi


import logging
logger = logging.getLogger("registry_log")


class FileCommand:
    DELETE = "DELETE"
    PRESERVE = "PRESERVE"
    UPLOAD = "UPLOAD"


class RegistrySpecificFieldsHandler(object):

    def __init__(self, registry_model, patient_model):
        self.registry_model = registry_model
        self.patient_model = patient_model
        self.mongo_wrapper = DynamicDataWrapper(self.patient_model)
        self.gridfs_api = GridFSApi(self.mongo_wrapper.get_filestore(self.registry_model.code))

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
                        file_wrapper = self.get_registry_specific_data()[self.registry_model.code][cde_model.code]
                        form_value = file_wrapper.gridfs_dict

                    elif form_value == FileCommand.DELETE:
                        self._delete_existing_file_in_gridfs(cde_model)
                        form_value = {}

                    logger.debug("file cde %s value = %s" % (cde_model.code, form_value))
                    processed_value = self._process_file_cde_value(cde_model, form_value)
                    logger.debug("after processing = %s" % processed_value)
                    mongo_patient_data[self.registry_model.code][cde_model.code] = processed_value

            logger.debug("************* registry specif data presave to Mongo: %s" % mongo_patient_data)

            self.mongo_wrapper.save_registry_specific_data(mongo_patient_data)

    def allowed_to_write_data(self):
        if self.registry_model.has_feature("family_linkage"):
            return self.patient_model.is_index
        else:
            return True

    def _delete_existing_file_in_gridfs(self, file_cde_model):
        existing_data = self.get_registry_specific_data()
        try:
            file_upload_wrapper = existing_data[self.registry_model.code][file_cde_model.code]
            if "gridfs_file_id" in file_upload_wrapper.mongo_data:
                original_gridfs_id = file_upload_wrapper.mongo_data["gridfs_file_id"]
                logger.debug("old value of file cde %s = %s" % (file_cde_model.code, original_gridfs_id))
                self.gridfs_api.delete(original_gridfs_id)
        except Exception, ex:
            logger.debug("error deleting existing file for %s: %s" % (file_cde_model.code, ex))

    def _process_file_cde_value(self, file_cde_model, form_value):
        if is_uploaded_file(form_value):
            self._delete_existing_file_in_gridfs(file_cde_model)
            gridfs_dict = self.gridfs_api.store(self.registry_model, self.patient_model, file_cde_model, form_value)
            return gridfs_dict
        else:
            return form_value

    def _get_file_form_value(self, file_cde_model, request):
        clear_key = file_cde_model.code + "-clear"
        if file_cde_model.code in request.FILES:
            logger.debug("file cde in request.FILES")
            in_memory_uploaded_file = request.FILES[file_cde_model.code]
            return in_memory_uploaded_file

        elif clear_key in request.POST:
            logger.debug("clear key %s in request.POST" % clear_key)
            clear_value = request.POST[clear_key]
            logger.debug("clear value = %s" % clear_value)
            if clear_value == "on":
                logger.debug("returning delete")
                return FileCommand.DELETE

        elif file_cde_model.code in request.POST:
            posted_value = request.POST[file_cde_model.code]
            logger.debug("file cde in request.POST value = %s" % posted_value)
            if posted_value == "":
                logger.debug("returning PRESERVE")
                return FileCommand.PRESERVE
            logger.debug("returning [%s]" % posted_value)
            return posted_value

        else:
            raise Exception("file cde not found")

    def get_registry_specific_fields(self, user):
        if self.registry_model not in user.registry.all():
            return []
        else:
            return self.registry_model.patient_fields

    def create_registry_specific_patient_form_class(self, user, form_class):
        additional_fields = SortedDict()
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
        logger.debug("reg spec fields from mongo = %s" % data)
        return data
