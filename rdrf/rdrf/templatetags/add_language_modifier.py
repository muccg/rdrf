from django import template
from django.conf import settings

register = template.Library()

@register.filter(name='add_language_modifier')
def add_language_modifier(file_name, request):
    """
    If the request ACCEPT_LANGUAGE header is non english then return a different file name
    """
    from rdrf.utils import get_language
    language = get_language(request)
    if language != "EN":
        return language + "_" + file_name
    return file_name
