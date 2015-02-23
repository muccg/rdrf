from django import template
register = template.Library()


@register.filter('widget_name')
def widget_name(obj):
    return obj.field.__class__.__name__
