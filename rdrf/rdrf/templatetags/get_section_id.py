from django import template

register = template.Library()


@register.filter()
def get_section_id(dictionary, key):
    return dictionary.get(key)
