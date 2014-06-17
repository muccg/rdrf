from django import template

register = template.Library()

@register.simple_tag
def sticky_registry(request):
    # return primary key of registry
    return request.session.get("sticky_registry",3)