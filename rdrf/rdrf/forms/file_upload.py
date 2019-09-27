import logging
from django.urls import reverse, NoReverseMatch
from django.core.files.uploadedfile import UploadedFile
from rdrf.db import filestorage

logger = logging.getLogger(__name__)


def is_upload_file(value):
    return isinstance(value, UploadedFile)


def is_filestorage_dict(value):
    return filestorage.get_id(value)


class FileUpload(object):

    """
    A wrapper to send to the django widget which will display the file upload
    :param data:
    :return:
    """

    def __init__(self, registry, cde_code, fs_dict):
        if isinstance(registry, str):
            from rdrf.models.definition.models import Registry
            self.registry = Registry.objects.get(code=registry)
        else:
            self.registry = registry
        self.cde_code = cde_code
        self.fs_dict = fs_dict

    @property
    def url(self):
        kwargs = {
            "registry_code": self.registry.code,
            "file_id": self.fs_dict.get("django_file_id"),
        }

        if kwargs["file_id"]:
            try:
                return reverse("file_upload", kwargs=kwargs)
            except NoReverseMatch:
                logger.warning("Couldn't make URL for file record %s" %
                               str(self.fs_dict))

        return ""

    def __str__(self):
        """
        This is to satisfy Django's ClearableFileInputWidget which
        uses django's force_text function
        """
        return self.fs_dict['file_name']

    @property
    def mongo_data(self):
        return self.fs_dict


def wrap_fs_data_for_form(registry, data):
    """
    :param data: Dynamic data loaded from Mongo
    fs data is stored like this:
    'cdecodeforfile': { "django_file_id' : 82327 , file_name: 'some name' }

    :return: --  Munges the passed in dictionary and wraps any fs references with
    wrappers which display a download link to the file
    """
    def wrap(value, key):
        if isinstance(value, list):
            return [wrap(item, key) for item in value]
        elif filestorage.get_id(value):
            return FileUpload(registry, key, value)
        elif isinstance(value, UploadedFile):
            return FileUpload(registry, key,
                              {"file_name": value.name, "django_file_id": 0})
        elif isinstance(value, dict):
            return {key: wrap(item, key) for key, item in value.items()}
        return value

    return wrap(data, None)


def wrap_file_cdes(registry_code, section_data, mongo_data, multisection=False, index_map={}):
    # Wrap file cde data for display in the form
    # I've refactored the code trying to make it as explicit as possible but it
    # would  still be good to refactor later as it is very painful
    # to debug.

    # The behaviour of file cdes/fields is as follows:

    # File CDEs are stored as dictionaries in Mongo : {"django_file_id": <fileid> , "name": <filename>}.
    # The filestorage module handles the actual file content and retrieval.

    # If no file has been uploaded modjgo data will contain the value None.

    # In the gui , the widget for a file cde shows a download link and a clear checkbox.
    # The download link is created by a wrapper class: "FileUpload".
    # The clear button if checked , results in a value of False in the django form cleaned data for that field.
    # If no file has been uploaded but one already exists for that cde in
    # mongo, the cleaned data actually has value None for that field.

    # The code below checks each key and value in the cleaned data of a section form ( or multisection formset)
    # If the field is not a file cde, the value is not unchanged ( i.e. not
    # wrapped)

    # If the field IS a file cde , we wrap the field's value ( or the
    # correspondign value in Mongo), appropriately.

    # For a single section section_data will be a dictionary
    # For multisections, section_data will be a list of section dictionaries

    # The special value of False in the cleaned form data for a file cde indicates the file has been cleared(deleted)
    # The value None means no file uploaded ( but there might already be data
    # uploaded in mongo)

    # So cases are: no upload and no data in mongo - don't wrap
    #               no upload but file already uploaded - wrap mongo data
    #               no upload and value False in form to indicate clearing - don't wrap
    #               upload of file : wrap form data

    from rdrf.helpers.utils import is_file_cde, get_code, get_form_section_code

    def is_existing_in_mongo(section_index, key, value):
        if mongo_data is None:
            return False
        if section_index is None:
            # section is not multi
            return value is None and key in mongo_data
        else:
            # multisection ...
            try:
                section_code = get_form_section_code(key)[-2]
                section_dict = mongo_data[section_code][section_index]
                return value is None and key in section_dict
            except BaseException:
                return False

    def should_wrap(section_index, key, value):
        try:
            cde_code = get_code(key)
        except BaseException:
            # not a delimited mongo key
            return False

        if is_file_cde(cde_code):
            u = is_upload_file(value)
            fs = is_filestorage_dict(value)
            im = is_existing_in_mongo(section_index, key, value)
            sw = u or fs or im
            return sw

        return False

    def wrap_upload(key, value):
        return FileUpload(registry_code, key, {"file_name": value.name, "django_file_id": 0})

    def wrap_filestorage_dict(key, value):
        return FileUpload(registry_code, key, value)

    def get_mongo_value(section_index, key):
        if section_index is None:
            value = mongo_data[key]
        else:
            section_code = get_form_section_code(key)[-2]
            section_dicts = mongo_data[section_code]
            correct_section_dict = section_dicts[section_index]
            value = correct_section_dict[key]
        return value

    def wrap(section_index, key, value):
        # NB we need section index in case we're looking inside a multisection
        # a multisection is just a list of section dicts indexed by
        # section_index
        if not should_wrap(section_index, key, value):
            return value

        if is_filestorage_dict(value):
            return wrap_filestorage_dict(key, value)

        if is_upload_file(value):
            return wrap_upload(key, value)

        if is_existing_in_mongo(section_index, key, value):
            mongo_value = get_mongo_value(section_index, key)
            return wrap_filestorage_dict(key, mongo_value)

    def wrap_section(section_index, section_dict):
        return {key: wrap(section_index, key, value) for key, value in section_dict.items()}

    def wrap_multisection(multisection_list):
        def iterate_over_non_deleted_items(multisection_list):
            # _if_ we have deleted items in the GUI, the passed in index_map
            # holds a map of new index --> original source index
            # so len(index_map.keys()) is the current number of items in the multisection
            # e.g.
            #  original items were A,B,C
            #  and we deleted item 2 (index 1) to produce A,C
            # index map would be {0: 0 ,
            #                     1: 2}
            # meaning that the first item hasn't changed but the 2nd item was originally 3rd

            # If C had a value of None for the file cde  this means we need to retrieve
            # the django  file id from the DB ,
            # but because we have deleted the second item and thus changed the index from 2 to 1
            # it would be an error to wrap the value of db item with index 1 - rather we need to
            # retieve the item using the old index  (2) ( which is preserved in the index_map dictionary
            # and we should extract _that_ to wrap for the form
            for new_index, item in enumerate(multisection_list):
                if index_map:
                    index = index_map[new_index]
                else:
                    index = new_index

                yield index, item

        return [wrap_section(section_index, section_dict) for section_index,
                section_dict in iterate_over_non_deleted_items(multisection_list)]

    if multisection:
        return wrap_multisection(section_data)
    else:
        return wrap_section(None, section_data)
