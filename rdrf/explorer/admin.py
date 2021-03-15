from django.contrib import admin
from .models import Query

from django.conf import settings
from rdrf.system_role import SystemRoles

if settings.SYSTEM_ROLE != SystemRoles.CIC_PROMS:
    class QueryAdmin(admin.ModelAdmin):

        list_display = ('title', 'description', 'created_by', 'created_at')
        list_filter = ('title',)

    admin.site.register(Query, QueryAdmin)
