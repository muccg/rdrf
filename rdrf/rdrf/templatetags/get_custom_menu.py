from django import template
from django.conf import settings

register = template.Library()

@register.assignment_tag
def get_custom_menu():
    items = getattr(settings, 'CUSTOM_MENU_ITEMS', [])
    return items
