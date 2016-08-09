from django.views.generic import View
from rdrf.models import Registry
from django.shortcuts import render_to_response, RequestContext
from django.http import Http404
from registry.groups.models import CustomUser
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from rdrf.utils import get_form_links
from django.utils.translation import ugettext_lazy as _
import logging

logger = logging.getLogger(__name__)


class MatrixRow(object):

    def __init__(self, permission, groups):
        self.permission = permission
        self.groups = groups   # auth groups

    @property
    def name(self):
        return _(self.permission.name)

    @property
    def columns(self):
        cols = []

        for group in self.groups:
            if self.has_permission(group):
                cols.append(True)
            else:
                cols.append(False)

        return cols

    def has_permission(self, group):
        return self.permission in [p for p in group.permissions.all()]


class PermissionMatrix(object):

    def __init__(self, registry_model):
        self.registry_model = registry_model
        self.groups = self._get_groups()
        self.permissions = self._get_permissions()

    def _get_groups(self):
        return Group.objects.all().order_by("name")

    def _get_permissions(self):
        return [p for p in Permission.objects.all().order_by("name")]

    def _get_users(self):
        return [u for u in CustomUser.objects.all().order_by("username")]

    @property
    def headers(self):
        return ["Permission"] + [_(group.name) for group in self.groups]

    @property
    def rows(self):
        row_objects = []
        for permission in self.permissions:
            row_objects.append(MatrixRow(permission, self.groups))
        return row_objects


class MatrixWrapper(object):

    def __init__(self, registry_model):
        self.matrix = PermissionMatrix(registry_model)
        self.name = "Permission Matrix for %s" % registry_model.name


class PermissionMatrixView(View):

    @method_decorator(login_required)
    def get(self, request, registry_code):
        try:
            registry_model = Registry.objects.get(code=registry_code)
        except Registry.DoesNotExist:
            return Http404("Registry with code %s does not exist" % registry_code)

        user = request.user
        context = {}
        context["location"] = "Permissions"
        context["matrix_wrapper"] = MatrixWrapper(registry_model)
        return render_to_response("rdrf_cdes/permission_matrix.html",
                                  context,
                                  context_instance=RequestContext(request))
