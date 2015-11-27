from django.http import HttpResponse
from django.views.generic import View
from django.core.urlresolvers import reverse
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required

from rdrf.models import Registry
from rdrf.context_browser import ContextBrowser

import json


class ContextsApiView(View):
    def get(self, request):
        registry_code = request.GET.get("registry_code")
        row_count = int(request.GET.get('rowCount', 20))
        search_phrase = request.GET.get("searchPhrase", None)
        current = int(request.GET.get("current", 1))
        registry_model = Registry.objects.get(code=registry_code)

        context_browser = ContextBrowser(request.user, registry_model)

        results = context_browser.do_search(search_phrase, row_count, current)

        return HttpResponse(json.dumps(results), content_type='application/json')
