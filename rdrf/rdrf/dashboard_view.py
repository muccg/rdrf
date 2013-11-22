from django.shortcuts import render_to_response, RequestContext
from django.views.generic.base import View
from django.core.context_processors import csrf
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

import logging

logger = logging.getLogger("registry_log")

class DashboardView(View):

    @method_decorator(login_required)
    def get(self, request):
        print request.user
        return render_to_response('rdrf_cdes/dashboard.html', context_instance=RequestContext(request))