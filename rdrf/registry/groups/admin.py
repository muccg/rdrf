from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model

from admin_forms import UserChangeForm, UserCreationForm
from models import WorkingGroup


class WorkingGroupAdmin(admin.ModelAdmin):
    search_fields = ["name"]

    def queryset(self, request):
        if request.user.is_superuser:
            return WorkingGroup.objects.all()

        user = User.objects.get(user=request.user)

        return WorkingGroup.objects.filter(id__in=user.working_groups.all())
    

class CustomUserAdmin(UserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm

    list_display = ('username', 'email', 'get_working_groups', 'get_registries')

    def get_form(self, request, obj=None, **kwargs):
        user = get_user_model().objects.get(username=request.user)
        form = super(CustomUserAdmin, self).get_form(request, obj, **kwargs)
        form.user = user
        return form

    def queryset(self, request):
        from itertools import chain
        from django.db.models import Q
    
        if request.user.is_superuser:
            return get_user_model().objects.all()
            
        filter1 = Q(working_groups__in=request.user.working_groups.all()) | Q(working_groups__isnull=True)
        filter2 = Q(registry__in=request.user.registry.all()) | Q(registry__isnull=True)
        
        filtered = get_user_model().objects.filter(filter1).distinct().filter(is_superuser = False)

        return filtered
    
    def get_working_groups(self, obj):
        works = ", ".join(reg.name for reg in obj.working_groups.all())
        return works

    def get_registries(self, obj):
        regs = ", ".join(reg.name for reg in obj.registry.all())
        return regs

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal information', {'fields': ('first_name', 'last_name', 'title', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'working_groups', 'registry')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2')}
        ),
    )
    
    get_working_groups.short_description = "Working Groups"
    get_registries.short_description = "Registries"

    search_fields = ('email',)
    ordering = ('email',)
    filter_horizontal = ()


admin.site.register(get_user_model(), CustomUserAdmin)
admin.site.register(WorkingGroup, WorkingGroupAdmin)
