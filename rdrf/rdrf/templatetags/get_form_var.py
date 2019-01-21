from django import template

register = template.Library()


@register.simple_tag
def get_form_var(dictionary, key):
    return dictionary.get(key)
