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
from datetime import datetime
import logging
logger = logging.getLogger(__name__)


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
        context["max_items"] = query_model.max_items
        context["columns"] = report_table.columns
        context["report_title"] = query_model.title
        context["api_url"] = reverse('report_datatable', args=[query_model_id])
        return render_to_response(
            'rdrf_cdes/report_table_view.html',
            context,
            context_instance=RequestContext(request))

    def _sanity_check(self, query_model, user):
        # todo sanity check
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
        logger.debug("query parameters = %s" % query_parameters)
        report_table = ReportTable(user, query_model)

        a = datetime.now()
        rows = report_table.run_query(query_parameters)
        logger.info("number of rows returned = %s" % len(rows))
        b = datetime.now()
        logger.debug("time to run query = %s" % (b - a))

        try:
            c = datetime.now()
            results_dict = self._build_result_dict(rows)
            j = self._json(results_dict)
            d = datetime.now()
            logger.info("time to jsonify = %s" % (d - c))
            return j
        except Exception, ex:
            logger.error("Could not jsonify results: %s" % ex)
            return self._json({})

    def _json(self, result_dict):
        json_data = json.dumps(result_dict)

        if self._validate_json(json_data):
            return HttpResponse(json_data, content_type="application/json")
        else:
            return HttpResponse(json.dumps(self._build_result_dict([])),
                                content_type="application/json")

    def _validate_json(self, json_data):
        try:
            data = json.loads(json_data)
        except ValueError:
            return False
        return True

    def _build_result_dict(self, rows):
        return {
            "recordsTotal": len(rows),
            "recordsFiltered": 0,
            "rows": rows,
        }

    def _get_query_parameters(self, request):
        p = {}
        p["search"] = request.POST.get("search[value]", None)
        p["search_regex"] = request.POST.get("search[regex]", False)
        sort_field, sort_direction = self._get_ordering(request)
        p["sort_field"] = sort_field
        p["sort_direction"] = sort_direction
        p["start"] = request.POST.get("start", 0)
        p["length"] = request.POST.get("length", 10)
        return p

    def _get_ordering(self, request):
        # columns[0][data]:full_name
        #...
        # order[0][column]:1
        # order[0][dir]:asc
        sort_column_index = None
        sort_direction = None
        for key in request.POST:
            if key.startswith("order"):
                if "[column]" in key:
                    sort_column_index = request.POST[key]
                elif "[dir]" in key:
                    sort_direction = request.POST[key]

        column_name = "columns[%s][data]" % sort_column_index
        sort_field = request.POST.get(column_name, None)

        return sort_field, sort_direction
