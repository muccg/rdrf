from django import template

register = template.Library()


@register.filter(name='add_language_modifier')
def add_language_modifier(file_name):
    """
    If the request ACCEPT_LANGUAGE header is non english then return a different file name
    """
    from django.utils.translation import get_language
    language = get_language().upper()

    if language != "EN":
        return language + "_" + file_name
    return file_name
