from django import template

register = template.Library()


@register.filter()
def is_abnormal(field):
    return field.field.cde.is_abnormal(field.value())
