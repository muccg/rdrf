from django import template

register = template.Library()

@register.filter()
def get_display_name(dictionary, key):
    return dictionary.get(key)
