from django import template

register = template.Library()


@register.filter()
def get_elements(dictionary, key):
    elements = dictionary.get(key)
    return ",".join(elements)
