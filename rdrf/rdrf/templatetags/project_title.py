from django import template
from django.conf import settings

register = template.Library()

@register.simple_tag
def project_title():
    try:
        return "%s" % (settings.PROJECT_TITLE)
    except:
        return "no_project_logo"
