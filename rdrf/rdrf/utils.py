from django.conf import settings


def get_code(delimited_key):
    return delimited_key.split(settings.FORM_SECTION_DELIMITER)[-1]


def get_form_section_code(delimited_key):
    return delimited_key.split(settings.FORM_SECTION_DELIMITER)


def mongo_key(form_name, section_code, cde_code):
    return settings.FORM_SECTION_DELIMITER.join([form_name, section_code, cde_code])


def id_on_page(registry_form_model, section_model, cde_model):
    return mongo_key(registry_form_model.name, section_model.code, cde_model.code)


def de_camelcase(s):
    """
    :param s: SomeFormName or someFormName
    :return: Some Form Name
    """
    i = 0
    l = len(s)

    def case_changed(x, y):
        return x.islower() and y.isupper()

    p = ""
    while i < l:
        c = s[i]
        p += c
        if i < l - 1:
            d = s[i + 1]
            if case_changed(c, d):
                p += " "
        i += 1

    return p


class FormLink(object):
    def __init__(self, patient_id, registry, registry_form, selected=False):
        self.registry = registry
        self.patient_id = patient_id
        self.form = registry_form
        self.selected = selected

    @property
    def url(self):
        from django.core.urlresolvers import reverse
        return reverse('registry_form', args=(self.registry.code, self.form.pk, self.patient_id))

    @property
    def text(self):
        return de_camelcase(self.form.name)