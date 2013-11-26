from django import template
import string

register = template.Library()

@register.filter()
def get_elements(dictionary, key):
    elements = dictionary.get(key)
    return ",".join(elements)
