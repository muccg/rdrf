from django import template

register = template.Library()


@register.filter()
def cde_display_value(value, cde):
    return cde.get_display_value(value)
