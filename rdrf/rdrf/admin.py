from django.contrib import admin
from django.core.urlresolvers import reverse
from models import *
#from registry.groups.models import User
import logging
from django.http import HttpResponse
from django.core.servers.basehttp import FileWrapper
import cStringIO as StringIO
from django.contrib import messages
from django.http import HttpResponseRedirect

from django.contrib.auth import get_user_model

logger = logging.getLogger("registry_log")


class SectionAdmin(admin.ModelAdmin):
    list_display = ('code', 'display_name')
    ordering = ['code']
    search_fields = ['code', 'display_name']

    def has_add_permission(self, request,*args, **kwargs):
        if request.user.is_superuser:
            return True
        return False

    def has_change_permission(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return True
        return False

    def has_delete_permission(self, request,  *args, **kwargs):
        if request.user.is_superuser:
            return True
        return False

class RegistryFormAdmin(admin.ModelAdmin):
    list_display = ('registry', 'name', 'sections', 'position')
    ordering = ['registry', 'name']

    list_filter = ['registry']

    def has_add_permission(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return True
        return False

    def has_change_permission(self, request,  *args, **kwargs):
        if request.user.is_superuser:
            return True
        return False

    def has_delete_permission(self, request,  *args, **kwargs):
        if request.user.is_superuser:
            return True
        return False



def export_registry_action(modeladmin, request, registry_models_selected):
    from datetime import datetime
    export_time = str(datetime.now())

    def export_registry(registry, request):
        from rdrf.exporter import Exporter
        exporter = Exporter(registry)
        logger.info("Exporting Registry %s" % registry.name)
        try:
            yaml_data, errors = exporter.export_yaml()
            if errors:
                logger.error("Error(s) exporting %s:" % registry.name)
                for error in errors:
                    logger.error("Export Error: %s" % error)
                    messages.error(request, "Error in export of %s: %s" % (registry.name, error))
                return None
            else:
                logger.info("Exported YAML Data for %s OK" % registry.name)
            return yaml_data
        except Exception, ex:
            logger.error("export registry action for %s error: %s" % (registry.name, ex))
            messages.error(request,"Custom Action Failed: %s" % ex)
            return None

    registrys = [ r for r in registry_models_selected ]

    if len(registrys) == 1:
            registry = registrys[0]
            yaml_export_filename = registry.name + '.yaml'
            yaml_data = export_registry(registry, request)
            if yaml_data is None:
                return HttpResponseRedirect("")

            myfile = StringIO.StringIO()
            myfile.write(yaml_data)
            myfile.flush()
            myfile.seek(0)

            response = HttpResponse(FileWrapper(myfile), content_type='text/yaml')
            yaml_export_filename = "export_%s_%s" % ( export_time, yaml_export_filename)
            response['Content-Disposition'] = 'attachment; filename="%s"' % yaml_export_filename

            return response
    else:
        import zipfile
        zippedfile = StringIO.StringIO()
        zf = zipfile.ZipFile(zippedfile, mode='w', compression=zipfile.ZIP_DEFLATED)

        for registry in registrys:
            yaml_data = export_registry(registry, request)
            if yaml_data is None:
                return HttpResponseRedirect("")

            zf.writestr(registry.code + '.yaml',yaml_data )

        zf.close()
        zippedfile.flush()
        zippedfile.seek(0)

        response = HttpResponse(FileWrapper(zippedfile), content_type='application/zip')
        name = "export_" + export_time + "_"  +  reduce(lambda x,y: x + '_and_' + y, [ r.code for r in registrys]) + ".zip"
        response['Content-Disposition'] = 'attachment; filename="%s"' % name

        return response

export_registry_action.short_description = "Export"

class RegistryAdmin(admin.ModelAdmin):
    actions = [export_registry_action]

    def queryset(self, request):
        if not request.user.is_superuser:
            user = get_user_model().objects.get(username=request.user)
            return Registry.objects.filter(registry__in=[reg.id for reg in user.registry.all()])

        return Registry.objects.all()

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
    
    def get_urls(self):
        original_urls = super(RegistryAdmin, self).get_urls()
        added_urls = []
        
        return original_urls

class QuestionnaireResponseAdmin(admin.ModelAdmin):
    list_display = ('registry', 'date_submitted', 'processed', 'process_link')
    list_filter = ('registry', 'date_submitted')
    
    
    def process_link(self, obj):
        link = "-"
        if not obj.processed:
            url = reverse('questionnaire_response', args=(obj.registry.code, obj.id))
            link = "<a href='%s'>Go</a>" % url
        return link
    
    process_link.allow_tags = True
    process_link.short_description = 'Process questionnaire'


def create_restricted_model_admin_class(model_class, search_fields=None, ordering=None):

    def query_set_func(model_class):
        def queryset(myself, request):
            if not request.user.is_superuser:
                return []
            else:
                return model_class.objects.all()

        return queryset

    def make_perm_func():
        def perm(self, request, *args, **kwargs):
            return request.user.is_superuser
        return perm

    overrides = {
        "has_add_permission": make_perm_func(),
        "has_change_permission": make_perm_func(),
        "has_delete_permission": make_perm_func(),
        "queryset" : query_set_func(model_class),
    }

    if search_fields:
        overrides["search_fields"] = search_fields
    if ordering:
        overrides["ordering"] = ordering

    return type(model_class.__name__ + "Admin" , (admin.ModelAdmin,), overrides)

admin.site.register(Registry, RegistryAdmin)
admin.site.register(QuestionnaireResponse, QuestionnaireResponseAdmin)
admin.site.register(CDEPermittedValue, create_restricted_model_admin_class(CDEPermittedValue, ordering=['code'], search_fields=['code', 'value']))
admin.site.register(CDEPermittedValueGroup, create_restricted_model_admin_class(CDEPermittedValueGroup, ordering=['code'], search_fields=['code']))
admin.site.register(CommonDataElement, create_restricted_model_admin_class(CommonDataElement, ordering=['code'], search_fields=['code', 'name']))
admin.site.register(RegistryForm, RegistryFormAdmin)

admin.site.register(Section, SectionAdmin)


