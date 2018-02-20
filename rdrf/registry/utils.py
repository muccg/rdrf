from django.conf import settings


def stripspaces(s):
    """Remove whitespace chars from both ends of the string returns a new
    string with whitespace chars removed from both ends of the string
    converts multiple whitespace chars into 1 space char returns an empty
    string if input is None or anything else than a string or unicode.
    """
    if s is None or not isinstance(s, str):
        return ""
    return " ".join(s.strip().split())


def get_static_url(url):
    """This method is simply to make formatting urls with static url shorter and tidier"""
    return "{0}{1}".format(settings.STATIC_URL, url)


def get_working_groups(user):
    return [working_group.id for working_group in user.working_groups.all()]


def get_registries(user):
    return [registry.id for registry in user.registry.all()]
