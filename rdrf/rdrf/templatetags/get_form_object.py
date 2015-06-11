from django import template

register = template.Library()


@register.filter()
def get_form_object(dictionary, key):
    return dictionary.get(key)
