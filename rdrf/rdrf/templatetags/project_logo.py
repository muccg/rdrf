from django import template
from django.conf import settings

register = template.Library()

@register.simple_tag
def project_logo():
    if hasattr(settings, "PROJECT_LOGO"):
        return "%s" % (settings.PROJECT_LOGO)
