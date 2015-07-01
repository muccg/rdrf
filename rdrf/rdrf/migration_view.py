import yaml
import json
import os
import pprint

from django.http import HttpResponse
from django.views.generic.base import View
from django.shortcuts import render_to_response, RequestContext

from django.db import connections


class MigrationView(View):

    def get(self, request):
        return render_to_response('rdrf_cdes/migration.html', context_instance=RequestContext(request))

    def post(self, request):
        sma_legacy = None
        sma_rdrf = None

        if request.FILES:
            sma_rdrf = yaml.load(request.FILES['rdrf_yaml'].read())
            sma_legacy = json.loads(request.FILES['legacy_json'].read())
            self.rdrf_legacy = sma_legacy

            context = {
                "legacy": sma_legacy,
                "rdrf": sma_rdrf,
            }
        else:
            results = []

            for item in request.POST:
                result = {}
                if "__rdrf" in item:
                    clean_rdrf_cde = item.replace("__rdrf", "")
                    result[clean_rdrf_cde] = request.POST["%s__legacy" % clean_rdrf_cde]
                    results.append(result)

            json_results = json.dumps(results, indent=4)
            response = HttpResponse(json_results)
            response['Content-Disposition'] = 'attachment; filename=migration_map.json'
            return response

        return render_to_response('rdrf_cdes/migration.html', context, context_instance=RequestContext(request))
