from django.forms import BaseForm

from django.utils.datastructures import SortedDict
from field_lookup import FieldFactory
from django.conf import settings

import re
import logging
logger = logging.getLogger("registry_log")


def log_everything(cls):
        for attr in cls.__dict__:
            value = getattr(cls, attr)
            logger.debug("log_everything value = %s" % value)
            if callable(value):
                logger.debug("XXXXXX creating new method for %s" % value)
                def make_new_method(value):
                    def new_func(*args, **kwargs):
                        logger.debug("calling %s(%s,%s)" % (value,args, kwargs))
                        ret_val = value(*args, **kwargs)
                        logger.debug("return value = %s" % ret_val)
                        return ret_val
                    return new_func

                setattr(cls,attr, make_new_method(value))
            else:
                logger.debug("Attribute %s with value %s not callable" % (attr,value))
        return cls


def create_form_class(owner_class_name):
    from models import CommonDataElement
    form_class_name = "CDEForm"
    cde_map = {}
    base_fields = {}

    for cde in CommonDataElement.objects.all().filter(owner=owner_class_name):
        cde_field = FieldFactory(cde).create_field()
        field_name = cde.code
        cde_map[field_name] = cde           # e.g.  "CDE0023" --> the cde element corresponding to this code
        base_fields[field_name] = cde_field   # a django field object

    class Media:
         css = {
            'all': ('dmd_admin.css',)
         }

    form_class_dict = {"base_fields": base_fields,
                       "cde_map": cde_map,
                       'Media': Media}

    form_class = type(form_class_name, (BaseForm,), form_class_dict)
    return form_class

def create_form_class_for_section(registry, registry_form, section, for_questionnaire=False, injected_model=None, injected_model_id=None):
    from models import CommonDataElement
    form_class_name = "SectionForm"
    base_fields = SortedDict()

    for s in section.elements.split(","):
        cde = CommonDataElement.objects.get(code=s.strip())
        cde_field = FieldFactory(registry, registry_form, section, cde, for_questionnaire, injected_model=injected_model, injected_model_id=injected_model_id).create_field()
        field_code_on_form = "%s%s%s%s%s" % (registry_form.name,settings.FORM_SECTION_DELIMITER,section.code,settings.FORM_SECTION_DELIMITER,cde.code)
        base_fields[field_code_on_form] = cde_field

    form_class_dict = {"base_fields": base_fields, "auto_id" : True}

    return type(form_class_name, (BaseForm,), form_class_dict)

