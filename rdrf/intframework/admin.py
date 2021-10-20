from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import HL7Mapping, HL7Message, HL7MessageFieldUpdate


class HL7MappingAdmin(admin.ModelAdmin):
    list_display = ("event_code", "event_map")


class UpdateInline(admin.StackedInline):
    model = HL7MessageFieldUpdate
    extra = 0


class HL7MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "created", "event_code", "username", "patient", "field_updates")
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


admin.site.register(HL7Mapping, HL7MappingAdmin)
admin.site.register(HL7Message, HL7MessageAdmin)
