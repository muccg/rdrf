from django import template

register = template.Library()


@register.filter(name='is_external')
def is_checkbox(element):
    """
    Is the element's value being supplied by an external system?
    """
    from intframework.utils import get_field_source
    field_source = get_field_source(element.name)
    return field_source == "external"
