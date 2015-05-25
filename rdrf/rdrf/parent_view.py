from django.views.generic.base import View
from django.shortcuts import render_to_response, RequestContext
from registry.patients.models import ParentGuardian


class ParentView(View):

    def get(self, request, registry_code):
        parent = ParentGuardian.objects.get(user = request.user)
        context = {
            'patients': parent.patient.all()
        }
        return render_to_response('rdrf_cdes/parent.html', context, context_instance=RequestContext(request))