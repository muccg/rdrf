from django import template
from django.forms.formsets import BaseFormSet

register = template.Library()


@register.filter()
def is_formset(dictionary, key):
    form_or_formset = dictionary.get(key)
    return isinstance(form_or_formset, BaseFormSet)
