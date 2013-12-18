from django.conf import settings
import logging

logger = logging.getLogger("registry_log")

class FileUpload(object):
    """
    A wrapper to send to the django widget which will display the file upload
    :param data:
    :return:
    """
    def __init__(self, registry, cde_code, gridfs_dict):
        self.registry = registry
        self.cde_code = cde_code
        self.gridfs_dict = gridfs_dict
        #self.url = "/uploads/%s/%s" % (str(self.gridfs_dict['gridfs_file_id'])

    @property
    def url(self):
        return "/%s/uploads/%s" % (self.registry, str(self.gridfs_dict['gridfs_file_id']))

    def __unicode__(self):
        """
        This is to satisfy Django's ClearableFileInputWidget which
        uses django's force_text function
        """
        return self.gridfs_dict['file_name']

def munge_uploaded_file_data(registry, data):
    """

    :param data: Dynamic data loaded from Mongo
    :return: --  nothing Munges the passed in dictionary

    """
    if data is None:
        return

    replacements = {}
    for key, value in data.items():
        logger.debug("checking %s %s" % (key, value))
        if isinstance(value, dict):
            if "gridfs_file_id" in value:
                wrapper = FileUpload(registry, key, value)
                logger.debug("munging gridfs %s data dict (before): %s -> (after) %s" % (key, value, wrapper))
                data[key] = wrapper

    return data