from django import template
from django.conf import settings
from django.utils.translation import ugettext as _

register = template.Library()

@register.simple_tag
def project_title():
    return _("%s" % (settings.PROJECT_TITLE))
