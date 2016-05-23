import logging
from django.core.urlresolvers import reverse, NoReverseMatch
from .models import CDEFile
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
        elif isinstance(value, dict):
            for key, item in value.items():
                value[key] = wrap(item, key)
        return value

    return wrap(data, None)
