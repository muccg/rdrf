from django import template

register = template.Library()


@register.assignment_tag
def get_form_var(dictionary, key):
    return dictionary.get(key)
