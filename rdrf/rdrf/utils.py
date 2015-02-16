from django.conf import settings
import logging

logger = logging.getLogger("registry_log")

def mongo_db_name(registry):
    return settings.MONGO_DB_PREFIX + registry

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

def get_user(username):
    from registry.groups.models import CustomUser
    try:
        return CustomUser.objects.get(username=username)
    except CustomUser.DoesNotExist:
        return None


def get_users(usernames):
    return filter(lambda x : x is not None, [ get_user(username) for username in usernames])


def has_feature(feature_name):
    if settings.FEATURES == "*":
        return True
    return feature_name in settings.FEATURES  # e.g. [ 'email_notification', 'adjudication' ]


def requires_feature(feature_name):
    def decorator(func):
        def wrapper(*args, **kwargs):
            if has_feature(feature_name):
                return func(*args, **kwargs)
            else:
                logger.info("%s will not be run with args %s kwargs %s as the site lacks feature %s" % (func.__name__, args, kwargs, feature_name))
        return wrapper
    return decorator

def get_full_link(partial_link, login_link=False):
    if login_link:
        # return a redirect login    https://rdrf.ccgapps.com.au/ophg/login?next=/ophg/admin/
        login_url = get_site_url() + "/login?next="
        return login_url + partial_link
    else:
        return site_url + partial_link


def get_site_url():
    # https://rdrf.ccgapps.com.au/ophg/admin/patients/patient/3/
    # ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    # this part !
    # todo get_site_url do this without analysing a request???
    return "http://localhost:8000"

