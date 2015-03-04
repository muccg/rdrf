from django import template
from rdrf import VERSION

register = template.Library()


# settings value
@register.simple_tag
def version_number():
    return VERSION
