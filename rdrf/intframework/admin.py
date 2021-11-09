from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import HL7Mapping, HL7Message, HL7MessageFieldUpdate, HL7MessageConfig


class HL7MappingAdmin(admin.ModelAdmin):
    list_display = ("event_code", "event_map")


class UpdateInline(admin.StackedInline):
    model = HL7MessageFieldUpdate
    extra = 0


class HL7MessageAdmin(admin.ModelAdmin):
    list_display = ("umrn", "created", "updated", "state", "event_code", "username", "patient", "field_updates")
    search_fields = ["umrn"]
    inlines = [
        UpdateInline,
    ]

    @mark_safe
    def patient(self, obj):
        link = ""
        if obj.patient_id:
            url = reverse("patient_edit", args=[obj.registry_code, obj.patient_id])
            link = f"<a href='{url}'>{obj.patient_id}</a>"
        return link

    @mark_safe
    def field_updates(self, obj):
        updates = ""
        if obj.updates.all().count():
            updates = "<table>"
            updates += "<tr><th>Field</th><th>HL7 path</th><th>Original value</th><th>Status</th><th>Failure reason</th></tr>"
            for u in obj.updates.all():
                updates += f"<tr><td>{u.data_field}</td><td>{u.hl7_path}</td><td>{u.original_value}</td>"
                updates += f"<td>{u.update_status}</td><td>{u.failure_reason}</td></tr>"
            updates += "</table>"
        return updates


class HL7MessageConfigAdmin(admin.ModelAdmin):
    list_display = ("event_code", "created", "updated", "config")
    search_fields = ["event_code"]


admin.site.register(HL7Mapping, HL7MappingAdmin)
admin.site.register(HL7Message, HL7MessageAdmin)
admin.site.register(HL7MessageConfig, HL7MessageConfigAdmin)
