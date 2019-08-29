from django import template
import pycountry

register = template.Library()


@register.simple_tag
def countries():
    return sorted(pycountry.countries, key=lambda c: c.name)
