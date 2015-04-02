from django import template

register = template.Library()


@register.assignment_tag
def get_form_element(dictionary, key):
    return dictionary[key]
