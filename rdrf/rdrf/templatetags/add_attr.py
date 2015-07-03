from django import template

register = template.Library()


@register.filter(name='add_attr')
def add_attr(field, param):
    attr, value = param.split(',')
    return field.as_widget(attrs={attr: value})
