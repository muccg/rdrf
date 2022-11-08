from django.contrib import admin
from dashboards.models import VisualisationConfig


class VisualisationConfigAdmin(admin.ModelAdmin):
    model = VisualisationConfig
    list_display = ("registry", "code")


admin.site.register(VisualisationConfig, VisualisationConfigAdmin)
