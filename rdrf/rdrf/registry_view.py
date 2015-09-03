from django.shortcuts import RequestContext
from django.shortcuts import render_to_response
from django.views.generic.base import View
from django.template.context_processors import csrf
from django.core.exceptions import ObjectDoesNotExist
import logging

from models import Registry

logger = logging.getLogger("registry_log")


class RegistryView(View):

    def get(self, request, registry_code):
        try:
            registry = Registry.objects.get(code=registry_code)
        except ObjectDoesNotExist:
            return render_to_response(
                'rdrf_cdes/splash.html', {'body': 'Oops, wrong registry code...'})

        context = {
            'body': registry.splash_screen,
            'registry_code': registry_code
        }

        context.update(csrf(request))
        return render_to_response(
            'rdrf_cdes/splash.html',
            context,
            context_instance=RequestContext(request))
