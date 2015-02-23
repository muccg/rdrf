from django import template

register = template.Library()


@register.filter()
def get_forms(dictionary, key):
    formset = dictionary.get(key)
    for form in formset:
        yield form
