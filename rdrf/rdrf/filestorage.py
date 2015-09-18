# Attempt to clean up the interaction with GridFS
import logging

logger = logging.getLogger("registry_log")


class GridFSApi(object):
    def __init__(self, gridfs_filestore):
        self.gridfs_filestore = gridfs_filestore

    def store(self, registry_model, patient_model, file_cde_model, file_like_object):
        """
        Store a file uploaded by a user into gridfs - return the the gridfs file id
        """
        original_filename = file_like_object.name
        gridfs_filename = self._get_gridfs_filename(registry_model, patient_model, file_cde_model, original_filename)
        added_file_id = self.gridfs_filestore.put(file_like_object.read(), filename=gridfs_filename)
        logger.info("wrote %s ( originally %s to grid fs: id = %s" % (gridfs_filename, original_filename, added_file_id))
        gridfs_ref_dict = {"gridfs_file_id": added_file_id, "file_name": original_filename}
        logger.debug("gridfs_ref_dict = %s" % gridfs_ref_dict)
        return gridfs_ref_dict

    def _get_gridfs_filename(self, registry_model, patient_model, file_cde_model, original_filename):
        return "%s_%s_%s_%s" % (registry_model.code, patient_model, file_cde_model.code, original_filename)
