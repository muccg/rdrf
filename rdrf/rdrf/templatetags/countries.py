from django import template
import pycountry

register = template.Library()

@register.assignment_tag
def countries():
    return pycountry.countries
