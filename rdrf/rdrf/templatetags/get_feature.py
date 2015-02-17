from django import template
from django.conf import settings
from rdrf.utils import has_feature
register = template.Library()

@register.assignment_tag
def get_feature(feature):
    return has_feature(feature)