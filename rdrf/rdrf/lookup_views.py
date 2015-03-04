from django.http import HttpResponse
from django.views.generic import View
import json

from registry.genetic.models import Gene, Laboratory
from registry.groups.models import CustomUser


import pycountry


class LookupView(View):

    MODEL = ""
    QUERY = ""
    ATTRS = {}

    def get(self, request):
        query = request.GET['term']

        results = self.MODEL.objects.filter(**{self.QUERY: query})

        json_results = []

        for r in results:
            json_ = {}
            json_['value'] = getattr(r, self.ATTRS['value'])
            json_['label'] = getattr(r, self.ATTRS['label'])
            json_results.append(json_)

        return HttpResponse(json.dumps(json_results))


class GeneView(LookupView):
    MODEL = Gene
    QUERY = 'symbol__icontains'
    ATTRS = {'value': 'symbol', 'label': 'name'}


class LaboratoryView(LookupView):
    MODEL = Laboratory
    QUERY = "name__icontains"
    ATTRS = {'value': 'id', 'label': 'name'}


class StateLookup(View):

    def get(self, request, country_code):
        state = None
        try:
            states = sorted(pycountry.subdivisions.get(country_code=country_code.upper()), key=lambda x: x.name)
            return HttpResponse(json.dumps(self._to_json(states)))
        except KeyError:
            return HttpResponse()

    def _to_json(self, states):
        json_result = []
        for state in states:
            json_ = {}
            json_['name'] = state.name
            json_['code'] = state.code
            json_['type'] = state.type
            json_['country_code'] = state.country_code
            json_result.append(json_)
        return json_result


class ClinitianLookup(View):
    
    def get(self, request):
        registry_code = request.GET['registry_code']
        all_users = CustomUser.objects.filter(registry__code = registry_code)
        filtered = [user for user in all_users if user.is_clinician and not user.is_superuser]
        
        json_result = []
        for clinician in filtered:
            for wg in clinician.working_groups.all():
                json_ = {}
                json_['full_name'] = "%s %s (%s)" % (clinician.first_name, clinician.last_name, wg.name)
                json_['id'] = "%d_%d" % (clinician.id, wg.id)
                json_result.append(json_)
        
        return HttpResponse(json.dumps(json_result))
