from django import template

register = template.Library()


@register.simple_tag
def get_form_element(dictionary, key):
    try:
        return dictionary[key]
    except KeyError:
        # need this case after adding cdepolicy ...
        # the None value is skipped on the form
        return None
