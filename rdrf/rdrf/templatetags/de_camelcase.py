from django import template

register = template.Library()


@register.filter
def de_camelcase(field):
    import re
    value = field[0].upper() + field[1:]
    chunks = re.findall('[A-Z][^A-Z]*', value)
    return " ".join(chunks)
