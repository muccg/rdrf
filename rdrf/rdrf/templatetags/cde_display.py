from django import template

register = template.Library()


@register.filter()
def cde_display_value(value, cde):
    # fixme: doesn't seem to work for all datatypes
    return cde.get_display_value(value)
