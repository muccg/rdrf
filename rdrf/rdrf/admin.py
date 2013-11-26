from django.contrib import admin
from models import *
from registry.groups.models import User

class SectionAdmin(admin.ModelAdmin):
    list_display = ('code', 'display_name')

class RegistryFormAdmin(admin.ModelAdmin):
    list_display = ('registry', 'name', 'sections')

class RegistryAdmin(admin.ModelAdmin):
    
    def queryset(self, request):
        if not request.user.is_superuser:
            user = User.objects.get(user=request.user)
            return Registry.objects.filter(registry__in=[reg.id for reg in user.registry.all()])
        return Registry.objects.all()

    def has_add_permission(self, request):
        if request.user.is_superuser:
            return True
        return False


admin.site.register(CDEPermittedValue)
admin.site.register(CDEPermittedValueGroup)
admin.site.register(CommonDataElement)
admin.site.register(Wizard)
admin.site.register(RegistryForm, RegistryFormAdmin)
admin.site.register(Section, SectionAdmin)
admin.site.register(Registry, RegistryAdmin)