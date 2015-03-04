from django import template

register = template.Library()


@register.filter()
def get_form(dictionary, key):
    return dictionary.get(key).as_table()
