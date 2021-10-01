from django.contrib import admin
from .models import HL7Mapping


class HL7MappingAdmin(admin.ModelAdmin):
    list_display = ('event_code', 'event_map')


admin.site.register(HL7Mapping, HL7MappingAdmin)
