from django import template
from django.conf import settings
from django.urls import reverse

register = template.Library()


@register.simple_tag
def project_title_link():
    url_name = settings.PROJECT_TITLE_LINK
    return reverse(url_name)
