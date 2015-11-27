from django.http import HttpResponse
from django.views.generic import View
from django.core.urlresolvers import reverse
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required

import json


class ContextsApiView(View):
    def get(self, registry_code):
        pass