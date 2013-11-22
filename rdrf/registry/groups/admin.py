from django import template
from django.conf.urls import patterns
from django.contrib import admin
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render_to_response
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext, ugettext_lazy as _
from admin_forms import *
from models import *


def list_username(user):
    return user.user.username
list_username.short_description = "Username"

def list_first_name(user):
    return user.user.first_name
list_first_name.short_description = "First name"

def list_last_name(user):
    return user.user.last_name.upper()
list_last_name.short_description = "Last name"


class UserAdmin(admin.ModelAdmin):
    list_display = [list_username, list_first_name, list_last_name, "title"]
    list_filter = ["title"]
    search_fields = ["user__username", "user__first_name", "user__last_name"]

    @transaction.commit_on_success
    def add_view(self, request, form_url="", extra_context=None):
        if not (self.has_change_permission(request) and self.has_add_permission(request)):
            raise PermissionDenied

        if request.method == "POST":
            form = UserNewForm(request.user, request.POST)
            if form.is_valid():
                import django.contrib.auth.models

                # Create the Django user.
                django_user = django.contrib.auth.models.User.objects.create_user(form.cleaned_data["username"], form.cleaned_data["email_address"], form.cleaned_data["password"])
                django_user.first_name = form.cleaned_data["first_name"]
                django_user.last_name = form.cleaned_data["last_name"]
                django_user.is_staff = True
                django_user.is_active = True
                django_user.save()

                # Set up the correct group.
                for group in form.cleaned_data["groups"]:
                    django_user.groups.add(group)
                    
                # Now create the internal user record.
                user = User(user=django_user)
                user.title = form.cleaned_data["title"]
                
                for working_group in form.cleaned_data["working_group"]:
                    user.working_groups.add(working_group)

                for registry in form.cleaned_data["registry"]:
                    user.registry.add(registry)

                user.save()
                return HttpResponseRedirect("../")
        else:
            form = UserNewForm(request.user)

        media = self.media + form.media

        return render_to_response("admin/groups/change_user.html", {
            "title": _("Add user"),
            "form": form,
            "is_popup": "_popup" in request.REQUEST,
            "add": True,
            "change": False,
            "has_add_permission": True,
            "has_delete_permission": False,
            "has_change_permission": True,
            "has_file_field": False,
            "has_absolute_url": False,
            "auto_populated_fields": (),
            "opts": self.model._meta,
            "save_as": False,
            #"root_path": self.admin_site.root_path,
            "app_label": self.model._meta.app_label,
            "media": mark_safe(media),
            "errors": form.errors,
        }, context_instance=template.RequestContext(request))

    def change_password(self, request, id):
        if not self.has_change_permission(request):
            raise PermissionDenied

        user = get_object_or_404(self.model, pk=id)

        if request.method == "POST":
            form = ChangePasswordForm(request.POST)
            if form.is_valid():
                user.user.set_password(form.cleaned_data["password"])
                user.user.save()

                return HttpResponseRedirect("../../")
        else:
            form = ChangePasswordForm()

        media = self.media + form.media

        return render_to_response("admin/groups/change_user.html", {
            "title": _("Change password: %s") % user,
            "form": form,
            "change": False,
            "is_popup": False,
            "add": False,
            "has_add_permission": False,
            "has_change_permission": True,
            "has_delete_permission": False,
            "has_file_field": False,
            "has_absolute_url": False,
            "auto_populated_fields": (),
            "opts": self.model._meta,
            "save_as": False,
            #"root_path": self.admin_site.root_path,
            "app_label": self.model._meta.app_label,
            "media": mark_safe(media),
            "errors": form.errors,
        }, context_instance=template.RequestContext(request))


    @transaction.commit_on_success
    def change_view(self, request, object_id, extra_context=None):
        if not self.has_change_permission(request):
            raise PermissionDenied

        user = get_object_or_404(self.model, pk=object_id)

        if request.method == "POST":
            form = UserChangeForm(request.user, request.POST)
            if form.is_valid():
                # Update the Django user.
                user.user.first_name = form.cleaned_data["first_name"]
                user.user.last_name = form.cleaned_data["last_name"]
                user.user.email = form.cleaned_data["email_address"] # Fix Trac #8, email wasn't saved when changed
                user.user.save()

                # Set up the correct group.
                user.user.groups.clear()
                for group in form.cleaned_data["groups"]:
                    user.user.groups.add(group)

                # Now update the internal user record.
                user.title = form.cleaned_data["title"]
                
                user.working_groups.clear()
                for working_group in form.cleaned_data["working_group"]:
                    user.working_groups.add(working_group)
                    
                user.registry.clear()
                for registry in form.cleaned_data["registry"]:
                    user.registry.add(registry)
                    
                user.save()

                return HttpResponseRedirect("../")
        else:
            form = UserChangeForm(request.user, {
                "first_name": user.user.first_name,
                "last_name": user.user.last_name,
                "email_address": user.user.email,
                "groups": [group.id for group in user.user.groups.all()],
                "title": user.title,
                "working_group": [working_group.id for working_group in user.working_groups.all()],
                "registry": [registry.id for registry in user.registry.all()]
            })

        media = self.media + form.media

        return render_to_response("admin/groups/change_user.html", {
            "title": _("Change user: %s") % user,
            "form": form,
            "is_popup": "_popup" in request.REQUEST,
            "add": False,
            "change": True,
            "show_delete": True,
            "has_add_permission": False,
            "has_delete_permission": False,#self.has_delete_permission(request),
            "has_change_permission": True,
            "has_file_field": False,
            "has_absolute_url": False,
            "auto_populated_fields": (),
            "opts": self.model._meta,
            "save_as": False,
            "app_label": self.model._meta.app_label,
            "media": mark_safe(media),
            "errors": form.errors,
        }, context_instance=template.RequestContext(request))

    def get_urls(self):
        urls = super(UserAdmin, self).get_urls()
        local_urls = patterns("",
            (r"^(\d+)/password/$", self.admin_site.admin_view(self.change_password))
        )
        return local_urls + urls

    def queryset(self, request):
        if request.user.is_superuser:
            return User.objects.all()

        user = User.objects.get(user=request.user)

        if self.has_change_permission(request):
            return User.objects.filter(working_groups__in=user.working_groups.all())
        else:
            return User.objects.none()


class WorkingGroupAdmin(admin.ModelAdmin):
    search_fields = ["name"]

    def queryset(self, request):
        if request.user.is_superuser:
            return WorkingGroup.objects.all()

        user = User.objects.get(user=request.user)

        return WorkingGroup.objects.filter(id__in=user.working_groups.all())

admin.site.register(User, UserAdmin)
admin.site.register(WorkingGroup, WorkingGroupAdmin)
