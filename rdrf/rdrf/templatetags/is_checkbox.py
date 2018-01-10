from django import template
from django.forms import CheckboxInput

register = template.Library()


@register.filter(name='is_checkbox')
def is_checkbox(element):
    """
    Depending on the template the input can be an element wrapper with a field attribute
    or a field object directly.
    """
    if hasattr(element, "field"):
        field = element.field

    if (field.widget.__class__.__name__ == CheckboxInput().__class__.__name__):

        return True
    return False
