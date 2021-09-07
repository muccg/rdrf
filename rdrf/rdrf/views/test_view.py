from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic.base import View
from rdrf.helpers.utils import anonymous_not_allowed
from registry.patients.models import Registry
from rdrf.models.definition.models import RegistryForm
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TestView(View):
    @method_decorator(anonymous_not_allowed)
    @method_decorator(login_required)
    def get(self, request):
        return render(request, "rdrf_cdes/test_page.html", {})


class TestDBView(View):
    def _get_template(self):
        return "rdrf_cdes/test_db_page.html"

    def format_time(self, t):
        return t.strftime("%m/%d/%Y, %H:%M:%S:%f")

    @method_decorator(anonymous_not_allowed)
    @method_decorator(login_required)
    def get(self, request):
        entered = datetime.now()
        registry = Registry.objects.first()
        registry_query = datetime.now()
        form = RegistryForm.objects.first()
        exited = datetime.now()
        registry_query_time = registry_query - entered
        form_query_time = exited - registry_query
        context = {"registry": registry,
                   "form": form,
                   "entry": self.format_time(entered),
                   "exit": self.format_time(exited),
                   "registry_query_time": registry_query_time,
                   "form_query_time": form_query_time,
                   }
        return render(request, self._get_template(), context)
