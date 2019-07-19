from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from .admin_forms import UserChangeForm, RDRFUserCreationForm
from .models import WorkingGroup
from useraudit.models import UserDeactivation

import logging

logger = logging.getLogger(__name__)


class WorkingGroupAdmin(admin.ModelAdmin):
    search_fields = ["name"]

    def get_queryset(self, request):
        if request.user.is_superuser:
            return WorkingGroup.objects.all()

        user = request.user

        return WorkingGroup.objects.filter(id__in=user.working_groups.all())


class CustomUserAdmin(UserAdmin):
    form = UserChangeForm
    add_form = RDRFUserCreationForm

    list_display = ('username', 'email', 'get_working_groups', 'get_registries', 'status')

    def get_form(self, request, obj=None, **kwargs):
        user = get_user_model().objects.get(username=request.user)
        creating_user_is_superuser = user.is_superuser
        form = super(CustomUserAdmin, self).get_form(request, obj, **kwargs)
        form.user = user
        # User creation is in two stages in Django admin
        if obj is None:
            # First stage: Ensure that the registry and working group selections are restricted
            form.CREATING_USER = request.user
            return form
        else:
            #  Second stage: Prevent user from adding a superuser now that we've given
            #  curators the ability to create users: To do this create a custom form which
            #  overrides clean based on the creating user

            if not creating_user_is_superuser:
                def modified_clean(myself):
                    cleaned_data = super(myself.__class__, myself).clean()
                    if "is_superuser" in cleaned_data:
                        if not creating_user_is_superuser and cleaned_data["is_superuser"]:
                            raise ValidationError(
                                "can't create a superuser unless you are one!")
                    return cleaned_data

                method_dict = {"clean": modified_clean}
                return type("LockedDownUserEditForm", (form,), method_dict)
            else:
                return form

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets

        if not request.user.is_superuser:
            return self.curator_fieldsets
        else:
            return super(UserAdmin, self).get_fieldsets(request, obj)

    def get_queryset(self, request):
        from django.db.models import Q

        if request.user.is_superuser:
            return get_user_model().objects.all()

        filter1 = Q(working_groups__in=request.user.working_groups.all()) | Q(
            working_groups__isnull=True)
        filter2 = Q(registry__in=request.user.registry.all())

        filtered = get_user_model().objects.filter(filter1).filter(
            filter2).distinct().filter(is_superuser=False)

        return filtered

    def get_working_groups(self, obj):
        works = ", ".join(reg.name for reg in obj.working_groups.all())
        return works

    def get_registries(self, obj):
        regs = ", ".join(reg.name for reg in obj.registry.all())
        return regs

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal information', {'fields': ('first_name', 'last_name', 'title', 'email', 'preferred_language')}),
        ('Permissions', {
         'fields': ('is_active', 'require_2_fact_auth', 'prevent_self_unlock', 'is_staff', 'is_superuser', 'groups', 'working_groups', 'registry')}),
    )

    # curators shouldn't see checkbox to create super user
    curator_fieldsets = (
        (None, {
            'fields': (
                'username', 'password')}), ('Personal information', {
                    'fields': (
                        'first_name', 'last_name', 'title', 'email')}), ('Permissions', {
                            'fields': (
                                'is_active', 'is_staff', 'groups', 'working_groups', 'registry')}))

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'registry', 'working_groups')}
         ),
    )

    get_working_groups.short_description = "Working Groups"
    get_registries.short_description = "Registries"

    search_fields = ('username', 'email')
    ordering = ('username',)
    filter_horizontal = ()

    def status(self, user):
        if user.is_active:
            return 'Active'
        choices = dict(UserDeactivation.DEACTIVATION_REASON_CHOICES)
        last_deactivation = UserDeactivation.objects.filter(
            username=user.username).order_by('-timestamp').first()
        if last_deactivation is None or last_deactivation.reason not in choices:
            return 'Inactive'

        reason = choices[last_deactivation.reason]

        return 'Inactive (%s)' % reason


admin.site.register(get_user_model(), CustomUserAdmin)
admin.site.register(WorkingGroup, WorkingGroupAdmin)
