from django.shortcuts import render_to_response, RequestContext
from django.views.generic.base import View
from django.core.context_processors import csrf
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

import logging

from registry.groups.models import User
from registry.patients.models import Patient
from registry.utils import get_registries

from models import RegistryForm

logger = logging.getLogger("registry_log")

class DashboardView(View):

    @method_decorator(login_required)
    def get(self, request):
        user = User.objects.get(user__username=request.user)

        context = {
            'user_obj': user,
            'patients': Patient.objects.get_filtered(user),
            'rdrf_forms': RegistryForm.objects.get_by_registry(get_registries(user))
        }
        return render_to_response('rdrf_cdes/dashboard.html', context, context_instance=RequestContext(request))