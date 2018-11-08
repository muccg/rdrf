from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def project_logo():
    if settings.PROJECT_LOGO is not None:
        return "%s" % (settings.PROJECT_LOGO)
