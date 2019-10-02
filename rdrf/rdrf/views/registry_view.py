from django.shortcuts import render
from django.views.generic.base import View
from django.template.context_processors import csrf
from django.core.exceptions import ObjectDoesNotExist
import logging

from django.utils.translation import ugettext as _

from rdrf.models.definition.models import Registry

logger = logging.getLogger(__name__)


class RegistryView(View):

    def get(self, request, registry_code):
        try:
            if registry_code != "admin":
                registry_model = Registry.objects.get(code=registry_code)
            else:
                return render(request, 'rdrf_cdes/splash.html',
                              {'body_expression': ' ', "state": "admin"})
        except ObjectDoesNotExist:
            return render(request, 'rdrf_cdes/splash.html',
                          {'body': _('This URL does not exist, or you are not logged in.'), "state": "missing"})

        context = {
            'splash_screen_template': "rdrf://model/Registry/%s/splash_screen" % registry_model.pk,
            'registry_code': registry_code,
            'state': "ok",
        }

        context.update(csrf(request))
        return render(request, 'rdrf_cdes/splash.html', context)
