from django.shortcuts import render_to_response, RequestContext
from django.views.generic.base import View

from rdrf.models import RegistryForm
from rdrf.models import Registry

class PatientView(View):

    def get(self, request, registry_code):
        context = {
            'registry_code': registry_code,
            'access': False
        }
        
        try:
            registry = Registry.objects.get(code=registry_code)
            if registry in request.user.registry.all():
                context['access']  = True
        except Registry.DoesNotExist:
            context['error_msg'] = "Registry does not exist"
        
        try:
            forms = RegistryForm.objects.filter(registry__code=registry_code).filter(is_questionnaire=True)
            context['forms'] = forms
        except RegistryForm.DoesNotExist:
            pass

        return render_to_response('rdrf_cdes/patient.html', context, context_instance=RequestContext(request))
