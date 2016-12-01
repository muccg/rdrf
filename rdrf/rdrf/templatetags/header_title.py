from django import template
from django.conf import settings

register = template.Library()

@register.simple_tag
def header_title():
    return "%s" % (settings.PROJECT_TITLE)
