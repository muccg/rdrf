from django import template

register = template.Library()


@register.filter
def has_feature(thing, feature):
    if hasattr(thing, "has_feature"):
        return thing.has_feature(feature)
    else:
        return False
