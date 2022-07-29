from django.shortcuts import render
from django.views.generic.base import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.db import transaction
from django.contrib.admin.views.decorators import staff_member_required

import logging
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)


def get_checkbox(d, key):
    try:
        value = d[key]
        return value == "on"
    except KeyError:
        return False


class ImportRegistryView(View):

    @method_decorator(staff_member_required)
    @method_decorator(login_required)
    def get(self, request):
        state = request.GET.get("state", "ready")
        user = get_user_model().objects.get(username=request.user)
        error_message = request.GET.get("error_message", None)

        context = {
            'user_obj': user,
            'state': state,
            'error_message': error_message,
        }

        return render(request, 'rdrf_cdes/import_registry.html', context)

    @method_decorator(staff_member_required)
    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        registry_yaml = request.POST["registry_yaml"]
        importer_options = {}

        just_cdes = get_checkbox(request.POST, "just_cdes")

        if just_cdes:
            importer_options["just_cdes"] = True

        from rdrf.services.io.defs.importer import Importer

        if request.FILES:
            registry_yaml = request.FILES['registry_yaml_file'].read()

        try:
            importer = Importer(importer_options)

            importer.load_yaml_from_string(registry_yaml)
            with transaction.atomic():
                importer.create_registry()

        except Exception as ex:
            logger.error("Import failed: %s" % ex)
            url_params = {
                "state": "fail",
                "error_message": str(ex),
            }
            import urllib.request
            import urllib.parse
            import urllib.error
            url_string = urllib.parse.urlencode(url_params)

            return HttpResponseRedirect(reverse('import_registry') + "?" + url_string)

        return HttpResponseRedirect(reverse('import_registry') + "?state=success")
