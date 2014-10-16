from django.conf import settings


def get_code(delimited_key):
    return delimited_key.split(settings.FORM_SECTION_DELIMITER)[-1]


def get_form_section_code(delimited_key):
    return delimited_key.split(settings.FORM_SECTION_DELIMITER)


def id_on_page(registry_form_model, section_model, cde_model):
    return settings.FORM_SECTION_DELIMITER.join([registry_form_model.name, section_model.code, cde_model.code])


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
