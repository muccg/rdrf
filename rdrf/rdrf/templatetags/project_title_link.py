from django import template
from django.conf import settings
from django.urls import reverse
from rdrf.system_role import SystemRoles

register = template.Library()


@register.simple_tag
def project_title_link():
    if not settings.SYSTEM_ROLE is SystemRoles.CIC_PROMS:
        url_name = settings.PROJECT_TITLE_LINK
        return reverse(url_name)
