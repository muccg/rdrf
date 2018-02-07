from django import template
from django.utils.translation import ugettext as _
register = template.Library()


@register.filter(name='translate')
def translate(s):
    return _(s)
