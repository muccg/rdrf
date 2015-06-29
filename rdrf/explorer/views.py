from django.http import HttpResponse
from django.shortcuts import render_to_response, redirect
from django.views.generic.base import View
from django.core.urlresolvers import reverse
from django.template import RequestContext
from django.core.exceptions import PermissionDenied
from django.contrib import messages

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from explorer import app_settings
from forms import QueryForm
from models import Query
from utils import DatabaseUtils
from rdrf.models import Registry
from registry.groups.models import WorkingGroup

import re
import csv
import json
import urllib2
from bson.json_util import dumps
from bson import json_util
from datetime import datetime
import collections


class LoginRequiredMixin(object):

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(LoginRequiredMixin, self).dispatch(
            request, *args, **kwargs)


class MainView(LoginRequiredMixin, View):

    def get(self, request):
        user = request.user
        
        reports = None
        
        if user.is_superuser:
            reports = Query.objects.all()
        elif user.is_curator:
            reports = Query.objects.filter(registry__in = [reg.id for reg in user.get_registries()]).filter(access_group__in = [g.id for g in user.get_groups()])
    
        return render_to_response(
            'explorer/query_list.html',
            {'object_list': reports},
            _get_default_params(request, None))


class NewQueryView(LoginRequiredMixin, View):

    def get(self, request):
        if not request.user.is_superuser:
            raise PermissionDenied()

        params = _get_default_params(request, QueryForm)
        return render_to_response('explorer/query.html', params)

    def post(self, request):
        if not request.user.is_superuser:
            raise PermissionDenied()

        query_form = QueryForm(request.POST)
        if query_form.is_valid():
            m = query_form.save(commit=False)
            m.save()
            query_form.save_m2m()
            return redirect(m)
        return HttpResponse()


class DeleteQueryView(LoginRequiredMixin, View):

    def get(self, request, query_id):
        if not request.user.is_superuser:
            raise PermissionDenied()    
    
        query_model = Query.objects.get(id=query_id)
        query_model.delete()
        return redirect('explorer_main')


class QueryView(LoginRequiredMixin, View):

    def get(self, request, query_id):
        from rdrf.models import Registry
        
        query_model = Query.objects.get(id=query_id)
        query_form = QueryForm(instance=query_model)
        params = _get_default_params(request, query_form)
        params['edit'] = True
        params['registries'] = Registry.objects.all()
        return render_to_response('explorer/query.html', params)

    def post(self, request, query_id):
        query_model = Query.objects.get(id=query_id)
        query_form = QueryForm(request.POST, instance=query_model)
        form = QueryForm(request.POST)

        database_utils = DatabaseUtils(form)

        if request.is_ajax():
            result = database_utils.run_full_query().result
            cdes = _get_cdes(query_model.registry)
            munged = _munge_docs(result, cdes)
            munged = _filler(munged, cdes)
            munged = _final_cleanup(munged)
    
            result = _human_friendly(munged)
            result_json = dumps(result, default=json_serial)
            return HttpResponse(result_json)
        else:
            if form.is_valid():
                m = query_form.save(commit=False)
                m.save()
                query_form.save_m2m()
                return redirect(m)


class DownloadQueryView(LoginRequiredMixin, View):

    def post(self, request, query_id):
        query_model = Query.objects.get(id=query_id)
        query_form = QueryForm(instance=query_model)
        
        query_params = re.findall("%(.*?)%", query_model.sql_query)
        
        sql_query = query_model.sql_query
        for param in query_params:
            sql_query = sql_query.replace("%%%s%%" % param, request.POST[param])        
        query_model.sql_query = sql_query
        
        if "registry" in query_params:
            query_model.registry = Registry.objects.get(id=request.POST["registry"])
        if "working_group" in query_params:
            query_model.working_group = WorkingGroup.objects.get(id=request.POST["working_group"])

        database_utils = DatabaseUtils(query_model)
        result = database_utils.run_full_query().result
        cdes = _get_cdes(query_model.registry)
        munged = _munge_docs(result, cdes)
        munged = _filler(munged, cdes)

        if not result:
            messages.add_message(request, messages.WARNING, "No results")
            return redirect(reverse("explorer_query_download", args=(query_id,)))            
        
        return self._extract(munged, query_model.title, query_id)
        

    def get(self, request, query_id):
        user = request.user
        query_model = Query.objects.get(id=query_id)
        query_form = QueryForm(instance=query_model)

        query_params = re.findall("%(.*?)%", query_model.sql_query)
        
        if query_params:
            params = _get_default_params(request, query_form)
            params['query_params'] = query_params
            if "registry" in query_params:
                params["registry"] = Registry.objects.all()
            if "working_group" in query_params:
                if user.is_curator:
                    params["working_group"] = WorkingGroup.objects.filter(id__in = [wg.id for wg in user.get_working_groups()])
                else:
                    params["working_group"] = WorkingGroup.objects.all()
            return render_to_response('explorer/query_download.html', params)
        
        database_utils = DatabaseUtils(query_model)        
        result = database_utils.run_full_query().result        
        cdes = _get_cdes(query_model.registry)
        munged = _munge_docs(result, cdes)
        munged = _filler(munged, cdes)
        munged = _final_cleanup(munged)
            
        return self._extract(munged, query_model.title, query_id)

    def _extract(self, result, title, query_id):
        result = _human_friendly(result)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="query_%s.csv"' %title.lower()
        writer = csv.writer(response)
        
        header = _get_header(result)
        writer.writerow(header)
        for r in result:
            row = _get_content(r, header)
            writer.writerow(row)

        return response

class SqlQueryView(View):

    def post(self, request):
        form = QueryForm(request.POST)
        database_utils = DatabaseUtils(form, True)
        results = database_utils.run_sql().result
        response = HttpResponse(dumps(results, default=json_serial))
        return response


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    serial = obj.isoformat()
    return serial


def _get_default_params(request, form):
        database_utils = DatabaseUtils()
        status, error = database_utils.connection_status()

        return RequestContext(request, {
            'version': app_settings.APP_VERSION,
            'host': app_settings.VIEWER_MONGO_HOST,
            'status': status,
            'error_msg': error,
            'form': form,
            'csrf_token_name': app_settings.CSRF_NAME
        })


def _get_header(result):
    header = []
    if result:
        for key in result[0].keys():
            header.append(key.encode("utf8"))
        return header


def _get_content(result, header):
    row = []
    for h in header:
        row.append(result[h.decode("utf8")])
    return row

def _human_friendly(result):
    for r in result:
        for key in r.keys():
            cde_value = _lookup_cde_value(r[key])
            if cde_value:
                r[key] = cde_value
            cde_name = _lookup_cde_name(key)
            if cde_name:
                r[cde_name] = r[key]
                del r[key]
    return result

def _lookup_cde_value(cde_value_code):
    from rdrf.models import CDEPermittedValue
    try:
        cde_permitedd_value_object = CDEPermittedValue.objects.get(code=cde_value_code)
        return cde_permitedd_value_object.value
    except CDEPermittedValue.DoesNotExist:
        return None
    except KeyError:
        return None

def _lookup_cde_name(cde_string):
    from rdrf.models import CommonDataElement
    try:
        cde_code = cde_string.split("____")[2]
        cde_object = CommonDataElement.objects.get(code=cde_code)
        return cde_object.name
    except CommonDataElement.DoesNotExist:
        return None
    except IndexError:
        return None

def _get_cdes(registry_obj):
    from rdrf.models import RegistryForm
    from rdrf.models import Section
    
    cdes = []
    forms = RegistryForm.objects.filter(registry__code=registry_obj.code)

    for form in forms:
        sections = Section.objects.filter(code__in=form.sections.split(","))
        for section in sections:
            for cde in section.get_elements():
                cdes.append("%s____%s____%s" % (form.name, section.code, cde))

    return cdes

def _filler(result, cdes):
    import collections
    munged = []
    for r in result:
        for cde in cdes:
            if cde not in r:
                r[cde] = "?"
        munged.append(collections.OrderedDict(sorted(r.items())))
    return munged

def _munge_docs(result, cdes):
    munged = []
    for res in result:
        munged_result = {}
        for item in res:
            if isinstance(res[item], list):
                res_list = []
                for i in res[item]:
                    res_list.append(i)
                munged_result[item] = res_list
            else:
                munged_result[item] = res[item]
        munged.append(munged_result)
    return munged

def _final_cleanup(results):
    for res in results:
        for key, value in res.iteritems():
            if key.endswith('timestamp'):
                del res[key]
    return results
