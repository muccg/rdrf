from django.http import HttpResponseRedirect
from django.views.generic import View
from django.http import HttpResponse

from models import Patient
from registry.groups.models import User

import json

class UnallocatedPatients(View):
    def get(self, request):
        user = User.objects.get(user__username=request.user)
        patients = Patient.objects.get_filtered_unallocated(user)
        results = [obj.as_json() for obj in patients]
        return HttpResponse(json.dumps(results), mimetype='application/json')
