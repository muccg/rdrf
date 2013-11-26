from django import template
import string

register = template.Library()

def js_quote(value):
    return "'" + value + "'"

@register.filter()
def get_elements(dictionary, key):
    elements = dictionary.get(key)
    return ",".join(map(js_quote,elements))
