import logging
import re
import gridfs
from bson.objectid import ObjectId
from .models import Registry, CDEFile
from .utils import models_from_mongo_key

logger = logging.getLogger(__name__)

__all__ = ["get_id", "delete_file_wrapper", "get_file",
           "store_file", "store_file_by_key"]

def get_id(value):
    if isinstance(value, dict):
        return value.get("gridfs_file_id") or value.get("django_file_id")
    return None

def delete_file_wrapper(fs, file_ref):
    gridfs_file_id = file_ref.get("gridfs_file_id")
    django_file_id = file_ref.get("django_file_id")
    logger.debug("existing file ids: gridfs = %s django = %s" % (gridfs_file_id, django_file_id))
    if gridfs_file_id is not None:
        if not fs.exists(gridfs_file_id):
            logger.info("%s did not exist in filestore" % gridfs_file_id)

        try:
            fs.delete(gridfs_file_id)
        except Exception, ex:
            logger.error("Error deleting file id %s in gridfs: %s" % (gridfs_file_id,
                                                                      ex))
            return None
        logger.debug("deleted gridfs file OK")
        return gridfs_file_id

    if django_file_id is not None:
        try:
            CDEFile.objects.get(id=django_file_id).delete()
        except CDEFile.DoesNotExist:
            logger.warning("Tried to delete CDEFile id=%s which doesn't exist" % django_file_id)
        except Exception as e:
            logger.exception("Couldn't delete CDEFile id=%s" % django_file_id)
        return django_file_id

    return None

def store_file(registry, cde, file_obj, form=None, section=None):
    cde_file = CDEFile(registry=registry,
                       form=form, section=section, cde=cde,
                       item=file_obj, filename=file_obj.name)
    cde_file.save()

    return {
        "django_file_id": cde_file.id,
        "file_name": file_obj.name
    }

def store_file_by_key(registry_code, patient_record, key, file_obj):
    registry = Registry.objects.get(code=registry_code)
    form, section, cde = models_from_mongo_key(registry, key)
    return store_file(registry, cde, file_obj, form, section)

oid_pat = re.compile(r"[0-9A-F]{24}", re.I)

def get_file(file_id, gridfs=None):
    if gridfs and oid_pat.match(str(file_id)):
        data = gridfs.get(ObjectId(file_id))
        filename = data.filename.split("****")[-1]
        return data, filename
    else:
        try:
            cde_file = CDEFile.objects.get(id=file_id)
            return cde_file.item, cde_file.filename
        except CDEFile.DoesNotExist:
            pass

    return None, None
