from django import template
from django.conf import settings

register = template.Library()


@register.assignment_tag
def get_custom_menu(request):
    items = getattr(settings, 'CUSTOM_MENU_ITEMS', [])

    for i in items:
        i['is_active'] = False
        if i['url'] == request.path:
            i['is_active'] = True

    return items
