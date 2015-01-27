from django import template
register = template.Library()

@register.simple_tag
def bar_chart(data):
    return "<h1>chart will go here!</h1>"
