from django.contrib import admin
from models import *
from registry.groups.models import User
import logging

logger = logging.getLogger("registry_log")


class SectionAdmin(admin.ModelAdmin):
    list_display = ('code', 'display_name')

    def has_add_permission(self, request,*args, **kwargs):
        if request.user.is_superuser:
            return True
        return False

    def has_change_permission(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return True
        return False

    def has_delete_permission(self, request,  *args, **kwargs):
        if request.user.is_superuser:
            return True
        return False

class RegistryFormAdmin(admin.ModelAdmin):
    list_display = ('registry', 'name', 'sections')

    def has_add_permission(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return True
        return False

    def has_change_permission(self, request,  *args, **kwargs):
        if request.user.is_superuser:
            return True
        return False

    def has_delete_permission(self, request,  *args, **kwargs):
        if request.user.is_superuser:
            return True
        return False



class RegistryAdmin(admin.ModelAdmin):
    
    def queryset(self, request):
        if not request.user.is_superuser:
            user = User.objects.get(user=request.user)
            return Registry.objects.filter(registry__in=[reg.id for reg in user.registry.all()])

        return Registry.objects.all()

    def has_add_permission(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return True
        return False

    def has_change_permission(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return True
        return False

    def has_delete_permission(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return True
        return False


def create_restricted_model_admin_class(model_class):

    def query_set_func(model_class):
        def queryset(myself, request):
            if not request.user.is_superuser:
                return []
            else:
                return model_class.objects.all()

        return queryset

    def make_perm_func():
        def perm(self, request, *args, **kwargs):
            return request.user.is_superuser
        return perm

    overrides = {
        "has_add_permission": make_perm_func(),
        "has_change_permission": make_perm_func(),
        "has_delete_permission": make_perm_func(),
        "queryset" : query_set_func(model_class),
    }
    return type(model_class.__name__ + "Admin" , (admin.ModelAdmin,), overrides)

admin.site.register(CDEPermittedValue, create_restricted_model_admin_class(CDEPermittedValue))
admin.site.register(CDEPermittedValueGroup, create_restricted_model_admin_class(CDEPermittedValueGroup))
admin.site.register(CommonDataElement, create_restricted_model_admin_class(CommonDataElement))
admin.site.register(RegistryForm, RegistryFormAdmin)
admin.site.register(QuestionnaireResponse)
admin.site.register(Section, SectionAdmin)

admin.site.register(Registry, RegistryAdmin)

logger.debug("%s" % dir(admin.site))

for attr in dir(admin.site):
    try:
        value = getattr(admin.site, attr)
        if not callable(value):
            logger.debug("site %s = %s" % (attr, value))
    except:
        pass

