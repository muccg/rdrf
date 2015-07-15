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
from rdrf.models import Registry, RegistryForm, Section, CommonDataElement, CDEPermittedValue
from registry.groups.models import WorkingGroup

import re
import csv
import json
import urllib2
from bson.json_util import dumps
from bson import json_util
from datetime import datetime
import collections
import logging
from itertools import product
from rdrf.utils import models_from_mongo_key, is_delimited_key, BadKeyError, cached

logger = logging.getLogger("registry_log")


def encode_row(row):
    return [s.encode('utf8') if type(s) is unicode else s for s in row]


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
            reports = Query.objects.filter(
                registry__in=[
                    reg.id for reg in user.get_registries()]).filter(
                access_group__in=[
                    g.id for g in user.get_groups()])

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
        registry_model = query_model.registry
        query_form = QueryForm(request.POST, instance=query_model)
        form = QueryForm(request.POST)

        database_utils = DatabaseUtils(form)

        if request.is_ajax():
            result = database_utils.run_full_query().result
            mongo_keys = _get_non_multiple_mongo_keys(registry_model)
            munged = _filler(result, mongo_keys)
            munged = _final_cleanup(munged)
            humaniser = Humaniser(registry_model)
            munged = MultisectionUnRoller(query_model.registry, humaniser).unroll_rows(munged)
            result = _human_friendly(registry_model, munged)
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
            query_model.working_group = WorkingGroup.objects.get(
                id=request.POST["working_group"])

        registry_model = query_model.registry
        database_utils = DatabaseUtils(query_model)
        result = database_utils.run_full_query().result
        mongo_keys = _get_non_multiple_mongo_keys(registry_model)
        munged = _filler(result, mongo_keys)
        humaniser = Humaniser(registry_model)
        munged = MultisectionUnRoller(query_model.registry, humaniser).unroll_rows(munged)
        logger.debug("number of unrolled rows = %s" % len(munged))

        if not munged:
            messages.add_message(request, messages.WARNING, "No results")
            return redirect(reverse("explorer_query_download", args=(query_id,)))

        return self._extract(registry_model, munged, query_model.title, query_id)

    def get(self, request, query_id):
        user = request.user
        query_model = Query.objects.get(id=query_id)
        registry_model = query_model.registry
        query_form = QueryForm(instance=query_model)

        query_params = re.findall("%(.*?)%", query_model.sql_query)

        if query_params:
            params = _get_default_params(request, query_form)
            params['query_params'] = query_params
            if "registry" in query_params:
                params["registry"] = Registry.objects.all()
            if "working_group" in query_params:
                if user.is_curator:
                    params["working_group"] = WorkingGroup.objects.filter(
                        id__in=[wg.id for wg in user.get_working_groups()])
                else:
                    params["working_group"] = WorkingGroup.objects.all()
            return render_to_response('explorer/query_download.html', params)

        database_utils = DatabaseUtils(query_model)
        result = database_utils.run_full_query().result
        #cdes = _get_cdes(query_model.registry)
        mongo_keys = _get_non_multiple_mongo_keys(query_model.registry)
        munged = _filler(munged, mongo_keys)
        munged = _final_cleanup(munged)

        return self._extract(registry_model, munged, query_model.title, query_id)

    def _extract(self, registry_model, result, title, query_id):
        result = _human_friendly(registry_model, result)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="query_%s.csv"' % title.lower()
        writer = csv.writer(response)

        header = _get_header(result)
        writer.writerow(encode_row(header))
        csv_rows = 0
        for r in result:
            row = _get_content(r, header)
            writer.writerow(encode_row(row))
            csv_rows += 1

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
        row.append(result.get(h.decode("utf8"), "?"))
    return row


class Humaniser(object):
    """
    If a display name/value is appropriate for a field, return it
    """
    def __init__(self, registry_model):
        self.registry_model = registry_model

    @cached
    def display_name(self, key):
        if is_delimited_key(key):
            try:
                form_model, section_model, cde_model = models_from_mongo_key(self.registry_model, key)
            except BadKeyError:
                logger.error("key %s refers to non-existant models" % key)
                return key

            human_name = "%s/%s/%s" % (form_model.name, section_model.display_name, cde_model.name)
            return human_name
        else:
            return key

    @cached
    def display_value(self, key, mongo_value):
        # return the display value for ranges
        if is_delimited_key(key):
            try:
                form_model, section_model, cde_model = models_from_mongo_key(self.registry_model, key)
            except BadKeyError:
                logger.error("Key %s refers to non-existant models" % key)
                return mongo_value

            if cde_model.pv_group:
                # look up the stored code and return the display value
                range_dict = cde_model.pv_group.as_dict()
                for value_dict in range_dict["values"]:
                    if mongo_value == value_dict["code"]:
                        return value_dict["value"]
        return mongo_value


def _human_friendly(registry_model, result):
    humaniser = Humaniser(registry_model)

    for r in result:
        for key in r.keys():
            mongo_value = r[key]
            cde_value = humaniser.display_value(key, mongo_value)
            if cde_value:
                r[key] = cde_value
            cde_name = humaniser.display_name(key)
            if cde_name:
                r[cde_name] = r[key]
                if cde_name != key:
                    del r[key]
    return result


def _get_non_multiple_mongo_keys(registry_model):
    # return a list of delimited mongo keys for the supplied registry
    # skip the generated questionnaire ( the data from which is copied to the target clinical forms anyway)
    # skip multisections  as these are handled separately
    delimited_keys = []
    from rdrf.utils import mongo_key_from_models
    for form_model in registry_model.forms:
        if not form_model.is_questionnaire:
            for section_model in form_model.section_models:
                if not section_model.allow_multiple:
                    for cde_model in section_model.cde_models:
                        delimited_key = mongo_key_from_models(form_model, section_model, cde_model)
                        delimited_keys.append(delimited_key)
    return delimited_keys




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


def _final_cleanup(results):
    for res in results:
        for key, value in res.iteritems():
            if key.endswith('timestamp'):
                del res[key]
    return results


class MultisectionUnRoller(object):
    def __init__(self, registry_model, humaniser):
        self.humaniser = humaniser
        self.registry_model = registry_model
        self.multisection_codes = self.get_multisection_codes()
        self.row_count = 0

    def get_multisection_codes(self):
        multisections = {}
        for form_model in self.registry_model.forms:
            if form_model.is_questionnaire:
                continue
            for section_model in form_model.section_models:
                if section_model.allow_multiple:
                    if not section_model.code in multisections:
                        multisections[section_model.code] = section_model
        return multisections

    def munge_multisection_item(self, multisection_code, item):
        multisection_model = self.multisection_codes[multisection_code]
        if isinstance(item, basestring):
            return self.create_blank_item(multisection_model)
        d = {}
        for key in item:
            if "____" in key:
                nice_cde_name = self.create_nice_name_from_delimited_key(multisection_model, key)
                d[nice_cde_name] = self.humaniser.display_value(key, item[key])
            else:
                # we omit the DELETE key and value
                pass
        return d

    def create_nice_name_from_delimited_key(self, multisection_model, delimited_key):
        from rdrf.models import CommonDataElement
        form_code, section_code, cde_code = delimited_key.split("____")
        cde_model = CommonDataElement.objects.get(code=cde_code)
        return self.nice_name(multisection_model, cde_model)

    def nice_name(self, section_model, cde_model):
        return section_model.display_name + "-" + cde_model.name

    def create_blank_item(self, multisection_model):
        d = {}
        for cde_model in multisection_model.cde_models:
            nice_name = self.nice_name(multisection_model, cde_model)
            d[nice_name] = "?"
        return d

    def unroll(self, row):
        """
        Basic idea is to use cartesian product to display all combinations of list elements
        for the multisections:
        if a row originally looks like   normalfield1, normalfield2, [a,b,c], notmalfield4, [d,e,f]
        we need to iterate through the cartesian product of [a,b,c] and [d,e,f] ( a square)
        ( 1 row expands to 9 rows !)
        Hence the use of itertools.product to walk through the generated choices
        ( eg b,e
             a,f
            etc etc)
        for three multisections we iterate through the triple product ( a cube) and so on
        This gets big quick obviously ...
        :param row:
        :return:
        """
        new_rows = []  # the extra unrolled rows
        sublists = {}  # a map of multisection codes to lists of the pairs of that multisection code and an item added

        for multisection_code in self.multisection_codes:
                if multisection_code in row:
                    multisection_data = row[multisection_code]
                    if type(multisection_data) is list:
                        for item in multisection_data:
                            munged_item = self.munge_multisection_item(multisection_code, item)
                            if multisection_code in sublists:
                                sublists[multisection_code].append((multisection_code, munged_item))
                            else:
                                sublists[multisection_code] = [(multisection_code, munged_item)]
                    else:
                        # the multisection has not been filled out so a ? appears in the report
                        blank_item = self.create_blank_item(self.multisection_codes[multisection_code])
                        if multisection_code in sublists:
                            sublists[multisection_code].append((multisection_code, blank_item))
                        else:
                            sublists[multisection_code] = [(multisection_code, blank_item)]

        f = 1
        for k in sublists:
            num_items = len(sublists[k])
            f = f * num_items

        row_count = 0
        # choice tuple is one choice from each sublist
        for choice_tuple in product(*sublists.values()):
            new_row = row.copy()
            row_count += 1
            for (key, new_dict) in choice_tuple:
                if key in new_row:
                    del new_row[key]
                new_row.update(new_dict)
            new_rows.append(new_row)

        return new_rows

    def unroll_rows(self, rows):
        self.row_count = 0
        new_rows = []
        for row in rows:
            unrolled_rows = self.unroll(row)
            self.row_count += len(unrolled_rows)
            new_rows.extend(unrolled_rows)

        return new_rows
