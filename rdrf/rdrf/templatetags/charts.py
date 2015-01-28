from django import template
register = template.Library()

@register.simple_tag
def pie_chart(parser, data):
    return "<h1>pie chart will go here!</h1>"


@register.simple_tag
def bar_chart(parser, data):
    return "<h1>bar chart will go here!</h1>"

