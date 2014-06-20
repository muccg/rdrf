from django.conf import settings

def get_code(delimited_key):
    return delimited_key.split(settings.FORM_SECTION_DELIMITER)[-1]

def get_form_section_code(delimited_key):
    return delimited_key.split(settings.FORM_SECTION_DELIMITER)

def id_on_page(registry_form_model, section_model, cde_model):
    return settings.FORM_SECTION_DELIMITER.join([registry_form_model.name, section_model.code, cde_model.code ])