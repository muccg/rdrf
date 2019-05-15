from django import template

register = template.Library()


@register.filter()
def is_abnormal(field):
    if field.errors:
        return False
    return field.field.cde.is_abnormal(field.value())
