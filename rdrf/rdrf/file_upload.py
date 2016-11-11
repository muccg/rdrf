from itertools import zip_longest, chain
import logging
from django.core.urlresolvers import reverse, NoReverseMatch
from django.core.files.uploadedfile import UploadedFile
from . import filestorage

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

    def __init__(self, registry, cde_code, gridfs_dict):
        if isinstance(registry, str):
            from rdrf.models import Registry
            self.registry = Registry.objects.get(code=registry)
        else:
            self.registry = registry
        self.cde_code = cde_code
        self.gridfs_dict = gridfs_dict

    @property
    def url(self):
        kwargs = {
            "registry_code": self.registry.code,
            "file_id": self.gridfs_dict.get("django_file_id"),
        }

        if kwargs["file_id"]:
            try:
                return reverse("file_upload", kwargs=kwargs)
            except NoReverseMatch:
                logger.info("Couldn't make URL for file record %s" %
                            str(self.gridfs_dict))

        return ""

    def __str__(self):
        """
        This is to satisfy Django's ClearableFileInputWidget which
        uses django's force_text function
        """
        return self.gridfs_dict['file_name']

    @property
    def mongo_data(self):
        return self.gridfs_dict


def wrap_gridfs_data_for_form(registry, data):
    """
    :param data: Dynamic data loaded from Mongo
    gridfs data is stored like this:
    'cdecodeforfile': { "gridfs_file_id' : 82327 , file_name: 'some name' }

    :return: --  Munges the passed in dictionary and wraps any gridfs references with
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


def wrap_file_cdes(registry_code, section_data, mongo_data, multisection=False):
    # Wrap file cde data for display in the form
    # I've refactored the code trying to make it as explicit as possible but it
    # would  still be good to refactor later as it is very painful
    # to debug.

    # The behaviour of file cdes/fields is as follows:

    # File CDEs are stored as dictionaries in Mongo : {"django_file_id": <fileid> , "name": <filename>}.
    # The filestorage module handles the actual file content and retrieval.

    # If no file has been uploaded mongo will contain the value None.

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

    from rdrf.utils import is_file_cde, get_code, get_form_section_code


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
            except:
                return False

    def should_wrap(section_index, key, value):
        try:
            cde_code = get_code(key)
        except:
            # not a delimited mongo key
            return False

        if is_file_cde(cde_code):
            u = is_upload_file(value)
            fs = is_filestorage_dict(value)
            im = is_existing_in_mongo(section_index, key, value)
            return u or fs or im

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
        return [wrap_section(section_index, section_dict) for section_index, section_dict in enumerate(multisection_list)]

    if multisection:
        return wrap_multisection(section_data)
    else:
        return wrap_section(None, section_data)
