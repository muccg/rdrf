from django.contrib import admin
from .models import Query


class QueryAdmin(admin.ModelAdmin):

    list_display = ('title', 'description', 'created_by', 'created_at')
    list_filter = ('title',)


admin.site.register(Query, QueryAdmin)
