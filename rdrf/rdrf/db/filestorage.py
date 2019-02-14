import logging
import re
from rdrf.models.definition.models import Registry, CDEFile
from rdrf.helpers.utils import models_from_mongo_key

logger = logging.getLogger(__name__)

__all__ = ["get_id", "delete_file_wrapper", "get_file",
           "store_file", "store_file_by_key"]


def get_id(value):
    if isinstance(value, dict):
        return value.get("django_file_id")
    return None


def delete_file_wrapper(file_ref):
    django_file_id = file_ref.get("django_file_id")
    if django_file_id is not None:
        try:
            CDEFile.objects.get(id=django_file_id).delete()
        except CDEFile.DoesNotExist:
            logger.warning("Tried to delete CDEFile id=%s which doesn't exist" % django_file_id)
        except Exception:
            logger.exception("Couldn't delete CDEFile id=%s" % django_file_id)
        return django_file_id

    return None


def store_file(registry_code, cde_code, file_obj, form_name=None, section_code=None):
    cde_file = CDEFile(registry_code=registry_code,
                       form_name=form_name,
                       section_code=section_code,
                       cde_code=cde_code,
                       item=file_obj,
                       filename=file_obj.name)
    cde_file.save()

    return {
        "django_file_id": cde_file.id,
        "file_name": file_obj.name
    }


def store_file_by_key(registry_code, patient_record, key, file_obj):
    registry = Registry.objects.get(code=registry_code)
    form, section, cde = models_from_mongo_key(registry, key)
    return store_file(registry_code,
                      cde.code,
                      file_obj,
                      form.name,
                      section.code)


oid_pat = re.compile(r"[0-9A-F]{24}", re.I)


def get_file(file_id):
    try:
        cde_file = CDEFile.objects.get(id=file_id)
        return cde_file.item, cde_file.filename
    except CDEFile.DoesNotExist:
        return None, None
