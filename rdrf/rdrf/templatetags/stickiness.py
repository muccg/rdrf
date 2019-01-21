from django import template
from rdrf.models.definition.models import Registry
from django.urls import reverse
from django.contrib.auth.models import AnonymousUser

DEFAULT_NAME = "Rare Disease Registry Framework"

register = template.Library()


@register.simple_tag
def sticky_registry(request):
    # return primary key of registry
    return request.session.get("sticky_registry", '')


@register.simple_tag
def current_registry(request):
    # If there is only one registry defined, use its name
    if Registry.objects.all().count() == 1:
        return Registry.objects.get().name

    # User only has one registry - so always return it
    if not isinstance(request.user, AnonymousUser) and request.user.num_registries == 1:
        current_registry = request.user.registry.get().name
    else:
        # User has access to more than one registry - use sticky value if possible
        try:
            current_registry = request.session.get("sticky_registry", DEFAULT_NAME)
        except AttributeError:
            current_registry = DEFAULT_NAME

        if current_registry != DEFAULT_NAME:
            # it is the "sticky" registry key set when selecting a registry to work with
            try:
                current_registry = Registry.objects.get(id=int(current_registry)).name
            except BaseException:
                current_registry = DEFAULT_NAME

    return current_registry


@register.simple_tag
def sticky_logout_url(request):
    registry_name = current_registry(request)
    if registry_name != DEFAULT_NAME:
        try:
            registry_object = Registry.objects.get(name=registry_name)
            return reverse("registry", kwargs={"registry_code": registry_object.code})
        except Registry.DoesNotExist:
            return reverse("landing")
    else:
        return reverse("landing")
