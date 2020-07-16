from django import template
from rdrf.models.definition.models import Registry

register = template.Library()


@register.simple_tag
def site_info():
    """
    Provide info about which registry is installed
    Only makes sense when one and only one installed
    """
    try:
        registry_model = Registry.objects.get()
        return registry_model.version
    except Registry.MultipleObjectsReturned:
        return ""
    except Registry.DoesNotExist:
        return ""
