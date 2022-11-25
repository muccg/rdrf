from django.contrib import admin
from dashboards.models import VisualisationConfig
from dashboards.models import VisualisationBaseDataConfig


class VisualisationConfigAdmin(admin.ModelAdmin):
    model = VisualisationConfig
    list_display = ("registry", "dashboard", "position", "code", "title")
    ordering = ("position",)


class VisualisationBaseDataConfigAdmin(admin.ModelAdmin):
    model = VisualisationBaseDataConfig
    list_display = ("registry",)


admin.site.register(VisualisationBaseDataConfig, VisualisationBaseDataConfigAdmin)
admin.site.register(VisualisationConfig, VisualisationConfigAdmin)
