from django.contrib import admin
from models import *

class SectionAdmin(admin.ModelAdmin):
    list_display = ('code', 'display_name')


admin.site.register(CDEPermittedValue)
admin.site.register(CDEPermittedValueGroup)
admin.site.register(CommonDataElement)
admin.site.register(Wizard)
admin.site.register(RegistryForm)
admin.site.register(Section, SectionAdmin)
admin.site.register(Registry)
