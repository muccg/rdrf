from django import template
from rdrf.utils import has_feature
register = template.Library()


@register.assignment_tag
def get_feature(feature):
    return has_feature(feature)
