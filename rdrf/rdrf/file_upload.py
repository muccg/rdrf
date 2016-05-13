import logging
from django.core.urlresolvers import reverse, NoReverseMatch
from .models import CDEFile
from .filestorage import FileStoreUtil

logger = logging.getLogger("registry_log")


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

    :return: --  nothing Munges the passed in dictionary and wraps any gridfs references with
    wrappers which display a download link to the file

    """
    logger.debug("in wrap_gridfs_data_for_form")

    def check_for_gridfs_dict(data):
        for key, value in data.items():
            logger.debug("checking key %s for gridfs data value = %s" % (key, value))
            if FileStoreUtil.get_id(value):
                logger.debug("found a gridfs dict - wrapping the value witha FileUpload object")
                wrapper = FileUpload(registry, key, value)
                logger.debug(
                    "munging gridfs %s data dict (before): %s -> (after) %s" %
                    (key, value, wrapper))
                data[key] = wrapper

    if data is None:
        logger.debug("supplied data is None - nothing to  do")
        return

    if isinstance(data, list):
        logger.debug("supplied data is a list - iterating ..")
        for data_dict in data:
            check_for_gridfs_dict(data_dict)
        return data

    elif isinstance(data, dict):
        logger.debug("supplied data is a dict - checking ...")
        check_for_gridfs_dict(data)
        return data

    return data
