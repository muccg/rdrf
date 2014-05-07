from django.shortcuts import render_to_response, RequestContext
from django.views.generic.base import View
from django.core.context_processors import csrf
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.db import transaction
from django.contrib.admin.views.decorators import staff_member_required

import logging
#from registry.groups.models import User
from django.contrib.auth import get_user_model

logger = logging.getLogger("registry_log")

class ImportRegistryView(View):


    @method_decorator(staff_member_required)
    @method_decorator(login_required)
    def get(self, request):

        state = request.GET.get("state","ready")
        user = get_user_model().objects.get(username=request.user)

        context = {
            'user_obj': user,
            'state': state,
        }


        return render_to_response('rdrf_cdes/import_registry.html', context, context_instance=RequestContext(request))

    @method_decorator(staff_member_required)
    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        import yaml
        registry_yaml = request.POST["registry_yaml"]

        from rdrf.importer import Importer

        if request.FILES:
            registry_yaml = request.FILES['registry_yaml_file'].read()

        try:
            importer = Importer()

            importer.load_yaml_from_string(registry_yaml)
            with transaction.commit_on_success():
                importer.create_registry()

        except Exception, ex:
            return HttpResponseRedirect(reverse('import_registry') + "?state=fail")

        return HttpResponseRedirect(reverse('import_registry') + "?state=success")



