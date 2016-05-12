from django.contrib import admin
from django.core.urlresolvers import reverse
from models import Registry
from models import RegistryForm
from models import QuestionnaireResponse
from models import CDEPermittedValue
from models import AdjudicationRequest
from models import AdjudicationResponse
from models import AdjudicationDecision
from models import AdjudicationDefinition
from models import Notification
from models import AdjudicationRequestState
from models import Adjudication
from models import CDEPermittedValueGroup
from models import CommonDataElement
from models import Section
from models import ConsentSection
from models import ConsentQuestion
from models import DemographicFields
from models import CdePolicy
from models import EmailNotification
from models import EmailTemplate
from models import EmailNotificationHistory

import logging
from django.http import HttpResponse
from django.core.servers.basehttp import FileWrapper
import cStringIO as StringIO
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.conf import settings

from django.contrib.auth import get_user_model

from rdrf.utils import has_feature
from admin_forms import RegistryFormAdminForm
from admin_forms import DemographicFieldsAdminForm
from functools import reduce

logger = logging.getLogger("registry_log")


class SectionAdmin(admin.ModelAdmin):
    list_display = ('code', 'display_name')
    ordering = ['code']
    search_fields = ['code', 'display_name']

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


class RegistryFormAdmin(admin.ModelAdmin):
    list_display = ('registry', 'name', 'is_questionnaire', 'position')
    ordering = ['registry', 'name']
    form = RegistryFormAdminForm

    list_filter = ['registry']

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
                    messages.error(request, "Error in export of %s: %s" %
                                   (registry.name, error))
                return None
            else:
                logger.info("Exported YAML Data for %s OK" % registry.name)
            return yaml_data
        except Exception as ex:
            logger.error("export registry action for %s error: %s" % (registry.name, ex))
            messages.error(request, "Custom Action Failed: %s" % ex)
            return None

    registrys = [r for r in registry_models_selected]

    if len(registrys) == 1:
        registry = registrys[0]
        yaml_export_filename = registry.name + ".yaml"
        yaml_data = export_registry(registry, request)
        if yaml_data is None:
            return HttpResponseRedirect("")

        myfile = StringIO.StringIO()
        myfile.write(yaml_data)
        myfile.flush()
        myfile.seek(0)

        response = HttpResponse(FileWrapper(myfile), content_type='text/yaml')
        yaml_export_filename = "export_%s_%s" % (export_time, yaml_export_filename)
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

            zf.writestr(registry.code + '.yaml', yaml_data)

        zf.close()
        zippedfile.flush()
        zippedfile.seek(0)

        response = HttpResponse(FileWrapper(zippedfile), content_type='application/zip')
        name = "export_" + export_time + "_" + \
            reduce(lambda x, y: x + '_and_' + y, [r.code for r in registrys]) + ".zip"
        response['Content-Disposition'] = 'attachment; filename="%s"' % name

        return response

export_registry_action.short_description = "Export"


def design_registry_action(modeladmin, request, registry_models_selected):
    if len(registry_models_selected) != 1:
        return
    else:
        registry = [r for r in registry_models_selected][0]
        return HttpResponseRedirect(reverse('rdrf_designer', args=(registry.pk,)))

design_registry_action.short_description = "Design"


def generate_questionnaire_action(modeladmin, request, registry_models_selected):
    for registry in registry_models_selected:
        registry.generate_questionnaire()

generate_questionnaire_action.short_description = "Generate Questionnaire"


class RegistryAdmin(admin.ModelAdmin):
    actions = [export_registry_action, design_registry_action, generate_questionnaire_action]

    def get_queryset(self, request):
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

        return original_urls

    def get_readonly_fields(self, request, obj=None):
        "Registry code is readonly after creation"
        return () if obj is None else ("code",)


class QuestionnaireResponseAdmin(admin.ModelAdmin):
    list_display = ('registry', 'date_submitted', 'process_link', 'name', 'date_of_birth')
    list_filter = ('registry', 'date_submitted')

    def process_link(self, obj):
        if not obj.has_mongo_data:
            return "NO DATA"

        link = "-"
        if not obj.processed:
            url = reverse('questionnaire_response', args=(obj.registry.code, obj.id))
            link = "<a href='%s'>Review</a>" % url
        return link

    def get_queryset(self, request):
        user = request.user
        if user.is_superuser:
            return QuestionnaireResponse.objects.all()
        else:
            return QuestionnaireResponse.objects.filter(
                registry__in=[
                    reg for reg in user.registry.all()])

    process_link.allow_tags = True
    process_link.short_description = 'Process questionnaire'


def create_restricted_model_admin_class(
        model_class,
        search_fields=None,
        ordering=None,
        list_display=None):

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
        "queryset": query_set_func(model_class),
    }

    if search_fields:
        overrides["search_fields"] = search_fields
    if ordering:
        overrides["ordering"] = ordering
    if list_display:
        overrides["list_display"] = list_display

    return type(model_class.__name__ + "Admin", (admin.ModelAdmin,), overrides)


class CDEPermittedValueAdmin(admin.StackedInline):
    model = CDEPermittedValue
    extra = 0

    fieldsets = (
        (None, {'fields': ('code', 'value', 'questionnaire_value', 'desc', 'position')}),
    )


class CDEPermittedValueGroupAdmin(admin.ModelAdmin):
    inlines = [CDEPermittedValueAdmin]


class AdjudicationRequestAdmin(admin.ModelAdmin):
    list_display = ('requesting_username', 'username', 'adjudicate_link')
    ordering = ['requesting_username', 'username']
    list_filter = ['requesting_username', 'username']

    def adjudicate_link(self, obj):
        if obj.state == AdjudicationRequestState.REQUESTED:
            url = obj.link
            url = "<a href='%s'>Adjudicate</a>" % url
            return url
        else:
            if obj.state == 'P':
                return "Done"
            elif obj.state == 'C':
                return "No ready"
            elif obj.state == 'I':
                return "Invalid"
            else:
                return "Unknown State:%s" % obj.state

    adjudicate_link.allow_tags = True
    adjudicate_link.short_description = 'Adjudication State'

    def queryset(self, request):
        user = request.user
        if user.is_superuser:
            return AdjudicationRequest.objects.all()
        else:
            return AdjudicationRequest.objects.filter(
                username=user.username,
                state=AdjudicationRequestState.REQUESTED)


class AdjudicationAdmin(admin.ModelAdmin):
    list_display = (
        'requesting_username', 'definition', 'requested', 'responded', 'adjudicate_link')
    ordering = ['requesting_username', 'definition']
    list_filter = ['requesting_username', 'definition']

    def adjudicate_link(self, obj):
        if obj.decision:
            return obj.decision.summary
        if obj.responded > 0:
            url = obj.link
            url = "<a href='%s'>Adjudicate</a>" % url
            return url
        else:
            return "-"

    adjudicate_link.allow_tags = True
    adjudicate_link.short_description = 'Adjudication'

    def queryset(self, request):
        user = request.user
        if user.is_superuser:
            return Adjudication.objects.all()
        else:
            return Adjudication.objects.filter(adjudicator_username=user.username)


class AdjudicationDefinitionAdmin(admin.ModelAdmin):
    list_display = ('registry', 'fields', 'result_fields')


class AdjudicationResponseAdmin(admin.ModelAdmin):
    list_display = ('request', 'response_data')


class AdjudicationDecisionAdmin(admin.ModelAdmin):
    list_display = ('definition', 'patient', 'decision_data')


class NotificationAdmin(admin.ModelAdmin):
    list_display = ('created', 'from_username', 'to_username', 'message')


class ConsentQuestionAdmin(admin.StackedInline):
    model = ConsentQuestion
    extra = 0

    fieldsets = (
        (None, {
            'fields': (
                'position', 'code', 'question_label', 'questionnaire_label', 'instructions')}), )


class ConsentSectionAdmin(admin.ModelAdmin):
    list_display = ('registry', 'section_label')
    inlines = [ConsentQuestionAdmin]


class DemographicFieldsAdmin(admin.ModelAdmin):
    model = DemographicFields
    form = DemographicFieldsAdminForm
    list_display = ("registry", "group", "field", "hidden", "readonly")


class CdePolicyAdmin(admin.ModelAdmin):
    model = CdePolicy
    list_display = ("registry", "cde", "groups", "condition")

    def groups(self, obj):
        return ", ".join([gr.name for gr in obj.groups_allowed.all()])

    groups.short_description = "Allowed Groups"

class EmailNotificationAdmin(admin.ModelAdmin):
    model = EmailNotification
    list_display = ("description", "registry", "email_from", "recipient", "group_recipient")

class EmailTemplateAdmin(admin.ModelAdmin):
    model = EmailTemplate
    list_display = ("language", "description")


class EmailNotificationHistoryAdmin(admin.ModelAdmin):
    model = EmailNotificationHistory
    list_display = ("date_stamp", "email_notification", "registry", "full_language", "resend")

    def registry(self, obj):
        return "%s (%s)" % (obj.email_notification.registry.name, obj.email_notification.registry.code.upper())

    def full_language(self, obj):
        return dict(settings.LANGUAGES)[obj.language]

    full_language.short_description = "Language"

    def resend(self, obj):
        email_url = reverse('resend_email', args=(obj.id,))
        return "<a class='btn btn-info btn-xs' href='%s'>Resend</a>" % email_url
    resend.allow_tags = True


admin.site.register(Registry, RegistryAdmin)
admin.site.register(QuestionnaireResponse, QuestionnaireResponseAdmin)
admin.site.register(
    CDEPermittedValue,
    create_restricted_model_admin_class(
        CDEPermittedValue,
        ordering=['code'],
        search_fields=[
            'code',
            'value',
            'pv_group__code'],
        list_display=[
            'code',
            'value',
            'questionnaire_value_formatted',
            'pvg_link',
            'position_formatted']))
admin.site.register(CDEPermittedValueGroup, CDEPermittedValueGroupAdmin)
# admin.site.register(CDEPermittedValueGroup, create_restricted_model_admin_class(CDEPermittedValueGroup, ordering=['code'], search_fields=['code']))
admin.site.register(
    CommonDataElement,
    create_restricted_model_admin_class(
        CommonDataElement,
        ordering=['code'],
        search_fields=[
            'code',
            'name',
            'datatype'],
        list_display=[
            'code',
            'name',
            'datatype',
            'widget_name']))
admin.site.register(RegistryForm, RegistryFormAdmin)

admin.site.register(Section, SectionAdmin)

admin.site.register(ConsentSection, ConsentSectionAdmin)

admin.site.register(DemographicFields, DemographicFieldsAdmin)

admin.site.register(CdePolicy, CdePolicyAdmin)

admin.site.register(EmailNotification, EmailNotificationAdmin)

admin.site.register(EmailTemplate, EmailTemplateAdmin)

admin.site.register(EmailNotificationHistory, EmailNotificationHistoryAdmin)

if has_feature('adjudication'):
    admin.site.register(Notification, NotificationAdmin)
    admin.site.register(Adjudication, AdjudicationAdmin)
    admin.site.register(AdjudicationDefinition, AdjudicationDefinitionAdmin)
    admin.site.register(AdjudicationRequest, AdjudicationRequestAdmin)
    admin.site.register(AdjudicationResponse, AdjudicationResponseAdmin)
    admin.site.register(AdjudicationDecision, AdjudicationDecisionAdmin)
