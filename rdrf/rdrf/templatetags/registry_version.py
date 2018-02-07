from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def registry_version(registry_code):
    pkg = __import__(registry_code)
    return "%s (%s)" % (pkg.VERSION, settings.FALLBACK_REGISTRY_CODE.upper())
