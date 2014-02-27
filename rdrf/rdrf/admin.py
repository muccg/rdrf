from django.contrib import admin
from models import *
from registry.groups.models import User
import logging
from django.http import HttpResponse
from django.core.servers.basehttp import FileWrapper
import cStringIO as StringIO

logger = logging.getLogger("registry_log")


class SectionAdmin(admin.ModelAdmin):
    list_display = ('code', 'display_name')

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
    list_display = ('registry', 'name', 'sections')

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

    def export_registry(registry):
        from rdrf.exporter import Exporter


        exporter = Exporter(registry)
        logger.info("Exporting Registry %s" % registry.name)
        try:
            yaml_data = exporter.export_yaml()
            logger.debug("Exported YAML Data for %s:" % registry.name)
            logger.debug(yaml_data)
            return yaml_data
        except Exception, ex:
            logger.error("Failed to export registry %s: %s" % (registry.name, ex))
            return None

    registrys = [ r for r in registry_models_selected ]

    if len(registrys) == 1:
            registry = registrys[0]
            yaml_export_filename = registry.name + '.yaml'
            yaml_data = export_registry(registry)

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
        yamls = [ export_registry(r) for f in registrys]
        zippedfile = StringIO.StringIO()
        zf = zipfile.ZipFile(zippedfile, mode='w', compression=zipfile.ZIP_DEFLATED)

        for registry in registrys:
            yaml_data = export_registry(registry)
            if yaml_data is None:
                yaml_data = "There was an error!"
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
            user = User.objects.get(user=request.user)
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


def create_restricted_model_admin_class(model_class):

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
    return type(model_class.__name__ + "Admin" , (admin.ModelAdmin,), overrides)

admin.site.register(CDEPermittedValue, create_restricted_model_admin_class(CDEPermittedValue))
admin.site.register(CDEPermittedValueGroup, create_restricted_model_admin_class(CDEPermittedValueGroup))
admin.site.register(CommonDataElement, create_restricted_model_admin_class(CommonDataElement))
admin.site.register(RegistryForm, RegistryFormAdmin)
admin.site.register(QuestionnaireResponse)
admin.site.register(Section, SectionAdmin)

admin.site.register(Registry, RegistryAdmin)

logger.debug("%s" % dir(admin.site))

for attr in dir(admin.site):
    try:
        value = getattr(admin.site, attr)
        if not callable(value):
            logger.debug("site %s = %s" % (attr, value))
    except:
        pass

