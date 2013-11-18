from django.forms import BaseForm
from field_lookup import FieldFactory


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

def create_form_class_for_section(section):
    from models import CommonDataElement
    from models import Section
    
    form_class_name = "SectionForm"
    
    section = Section.objects.get(code=section)
    base_fields = {}
    for s in section.elements.split(","):
        cde = CommonDataElement.objects.get(code=s)
        cde_field = FieldFactory(cde).create_field()
        base_fields[cde.code] = cde_field

    form_class_dict = {"base_fields": base_fields, "auto_id" : True}
    
    return type(form_class_name, (BaseForm,), form_class_dict)