from django import template
from rdrf.models import Registry

register = template.Library()

@register.simple_tag
def sticky_registry(request):
    # return primary key of registry
    return request.session.get("sticky_registry", '')

@register.simple_tag
def current_registry(request):
    DEFAULT_NAME = "Rare Disease Registry Framework"
    # If there is only one registry defined, use its name
    if Registry.objects.all().count() == 1:
        return Registry.objects.get().name

    # User only has one registry - so always return it
    if request.user.num_registries == 1:
        current_registry = request.user.registry.get().name
    else:
        # User has access to more than one registry - use sticky value if possible
        current_registry = request.session.get("sticky_registry", DEFAULT_NAME)
        if current_registry != DEFAULT_NAME:
            # it is the "sticky" registry key set when selecting a registry to work with
            try:
                current_registry = Registry.objects.get(id=int(current_registry)).name
            except:
                current_registry = DEFAULT_NAME

    return current_registry