from django import template
from django.forms.formsets import BaseFormSet

register = template.Library()


@register.filter()
def is_formset_obj(obj):
    return isinstance(obj, BaseFormSet)
