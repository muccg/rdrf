from django import template
from django.conf import settings

register = template.Library()

@register.simple_tag
def project_logo_padding():
    if hasattr(settings, "PROJECT_LOGO_PADDING"):
        return "%s" % (settings.PROJECT_LOGO_PADDING)
