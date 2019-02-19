from django import template
from django.conf import settings
from django.urls import reverse
from rdrf.system_role import SystemRoles

register = template.Library()

_HOME_PAGE = "admin:index"


@register.simple_tag
def project_title_link():
    if settings.SYSTEM_ROLE is SystemRoles.CIC_PROMS:
        return reverse(_HOME_PAGE)
    else:
        url_name = settings.PROJECT_TITLE_LINK
        return reverse(url_name)
