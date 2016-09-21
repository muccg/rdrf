from itertools import izip_longest, chain
import logging
from django.core.urlresolvers import reverse, NoReverseMatch
from django.core.files.uploadedfile import UploadedFile
from . import filestorage

logger = logging.getLogger(__name__)


class FileUpload(object):

    """
    A wrapper to send to the django widget which will display the file upload
    :param data:
    :return:
    """

    def __init__(self, registry, cde_code, gridfs_dict):
        if isinstance(registry, unicode):
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
            "file_id": (self.gridfs_dict.get("django_file_id") or
                        self.gridfs_dict.get("gridfs_file_id")),
        }

        if kwargs["file_id"]:
            try:
                return reverse("file_upload", kwargs=kwargs)
            except NoReverseMatch:
                logger.info("Couldn't make URL for file record %s" % str(self.gridfs_dict))

        return ""

    def __unicode__(self):
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
            return { key: wrap(item, key) for key, item in value.items() }
        return value

    return wrap(data, None)


def merge_gridfs_data_for_form(registry, form_data, dyn_patient):
    """
    Merges existing patient mongo from dyn_patient into form_data, if
    it's missing.
    Because form_data is cleaned_data from a Django form, file uploads
    are missing. In order to display the currently existing files,
    they need to be copied over from dyn_patient.
    """
    def merge(form, dyn, key):
        if form is False:
            pass  # deleted file
        elif isinstance(form, list) and isinstance(dyn, list):
            return [merge(form_item, dyn_item, key)
                    for (form_item, dyn_item) in izip_longest(form, dyn)
                    if form_item is not False]
        elif isinstance(form, UploadedFile):
            return FileUpload(registry, key,
                              {"file_name": form.name, "django_file_id": 0})
        elif isinstance(form, FileUpload):
            return form
        elif not filestorage.get_id(form) and filestorage.get_id(dyn):
            return FileUpload(registry, key, dyn)
        elif isinstance(form, dict) and isinstance(dyn, dict):
            for key, item in form.items():
                form[key] = merge(item, dyn.get(key), key)
        return form

    return merge(form_data, dyn_patient, None)

def merge_gridfs_data_for_form_multi(registry, form_data, dyn_patient):
    """
    Merges multisection mongo file data into the form fields.
    """
    flat_dyn = chain.from_iterable(v for k, v in dyn_patient.items()
                                   if isinstance(v, list))
    return merge_gridfs_data_for_form(registry, form_data, list(flat_dyn))
