from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def project_stylesheet():
    if hasattr(settings, "PROJECT_STYLESHEET"):
        return "%s" % (settings.PROJECT_STYLESHEET)
