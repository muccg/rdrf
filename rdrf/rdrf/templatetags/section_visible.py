from django import template
from django.conf import settings

register = template.Library()


import logging
logger = logging.getLogger(__name__)

@register.simple_tag
def section_visible(section, form):
    for name, s in section:
        for f in form:
            logger.debug(f)

