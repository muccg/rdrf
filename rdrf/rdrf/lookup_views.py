from django.http import HttpResponse
from django.views.generic import View
import json

from registry.genetic.models import Gene, Laboratory

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