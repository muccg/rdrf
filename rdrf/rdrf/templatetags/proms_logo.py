from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def proms_logo():
    if settings.PROMS_LOGO is not None:
        return "%s" % (settings.PROMS_LOGO)
