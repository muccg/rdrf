from django.http import HttpResponse
from django.views.generic import View
import json

from registry.genetic.models import Gene, Laboratory

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
    ATTRS = {'value': 'symbol', 'label': 'name' }
    

class LaboratoryView(LookupView):
    MODEL = Laboratory
    QUERY = "name__icontains"
    ATTRS = {'value': 'id', 'label': 'name' }


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
