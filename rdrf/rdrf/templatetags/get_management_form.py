from django import template

register = template.Library()


@register.filter()
def get_management_form(dictionary, key):
    formset = dictionary.get(key)
    return formset.management_form
