from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def project_logo_link():
    if settings.PROJECT_LOGO_LINK is not None:
        return "%s" % (settings.PROJECT_LOGO_LINK)
