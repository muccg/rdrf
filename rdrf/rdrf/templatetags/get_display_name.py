from django import template
from django.utils.translation import ugettext_lazy as _

register = template.Library()


@register.filter()
def get_display_name(dictionary, key):
    return _(dictionary.get(key))
