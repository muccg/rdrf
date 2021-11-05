from django import template
from intframework.utils import get_field_source

register = template.Library()


@register.filter(name='is_external')
def is_external(element):
    """
    Is the element's value being supplied by an external system?
    """
    if hasattr(element, "code"):
        field_source = get_field_source(element.code)
    else:
        field_source = get_field_source(element.name)
    return field_source == "external"
