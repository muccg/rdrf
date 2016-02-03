from django.shortcuts import render_to_response, RequestContext
from django.views.generic.base import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.http import HttpResponseRedirect
from django.http import Http404
from django.http import HttpResponse
from django.core.urlresolvers import reverse

from explorer.models import Query

from rdrf.reporting_table import ReportTable
import json


class LoginRequiredMixin(object):

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(LoginRequiredMixin, self).dispatch(
            request, *args, **kwargs)


class ReportView(LoginRequiredMixin, View):

    def get(self, request):
        user = request.user

        reports = None

        if user.is_superuser:
            reports = Query.objects.all()
        elif user.is_curator:
            reports = Query.objects.filter(
                registry__in=[
                    reg.id for reg in user.get_registries()]).filter(
                access_group__in=[
                    g.id for g in user.get_groups()])

        context = {}
        context['reports'] = reports
        context["location"] = 'Reports'
        return render_to_response(
            'rdrf_cdes/reports.html',
            context,
            context_instance=RequestContext(request))


class ReportDataTableView(LoginRequiredMixin, View):
    def get(self, request, query_model_id):
        user = request.user
        try:
            query_model = Query.objects.get(pk=query_model_id)
        except Query.DoesNotExist:
            raise Http404("Report %s does not exist" % query_model_id)

        if not self._sanity_check(query_model, user):
            return HttpResponseRedirect("/")

        report_table = ReportTable(user, query_model)
        registry_model = query_model.registry

        context = {}
        context["location"] = report_table.title
        context["registry_code"] = registry_model.code
        context["columns"] = report_table.columns
        context["api_url"] = reverse('report_datatable', args=[query_model_id])
        return render_to_response(
            'rdrf_cdes/report_table_view.html',
            context,
            context_instance=RequestContext(request))

    def _sanity_check(self, query_model, user):
        #todo sanity check
        return True

    def post(self, request, query_model_id):
        user = request.user
        try:
            query_model = Query.objects.get(pk=query_model_id)
        except Query.DoesNotExist:
            raise Http404("Report %s does not exist" % query_model_id)

        if not self._sanity_check(query_model, user):
            return HttpResponseRedirect("/")

        query_parameters = self._get_query_parameters(request)
        report_table = ReportTable(user, query_model)
        rows = [row for row in report_table.run_query(query_parameters)]
        return self._json(self._build_result_dict(rows))


    def _json(self, result_dict):
        json_data = json.dumps(result_dict)
        return HttpResponse(json_data, content_type="application/json")

    def _build_result_dict(self, rows):
        return {
            "draw": 100,
            "recordsTotal": len(rows),
            "recordsFiltered": 0,
            "rows": rows,
        }

    def _get_query_parameters(self, request):
        p = {}
        p["search"] = request.POST.get("search[value]", None)
        p["search_regex"] = request.POST.get("search[regex]", False)














