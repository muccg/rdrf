from django.contrib import admin
from dashboards.models import VisualisationConfig
from dashboards.models import VisualisationBaseDataConfig


class VisualisationConfigAdmin(admin.ModelAdmin):
    model = VisualisationConfig
    list_display = ("registry", "dashboard", "position", "code", "title")
    ordering = (
        "registry",
        "dashboard",
        "position",
    )

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


class VisualisationBaseDataConfigAdmin(admin.ModelAdmin):
    model = VisualisationBaseDataConfig
    list_display = ("registry", "code", "created", "updated", "state")
    exclude = ("data",)
    ordering = ("registry", "code")

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


admin.site.register(VisualisationBaseDataConfig, VisualisationBaseDataConfigAdmin)
admin.site.register(VisualisationConfig, VisualisationConfigAdmin)
