from django.http import HttpResponse
from django.views.generic import View
import json

from registry.genetic.models import Gene, Laboratory
from registry.groups.models import CustomUser

import pycountry

import logging
logger = logging.getLogger("registry_log")


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
    ATTRS = {'value': 'symbol', 'label': 'name'}


class LaboratoryView(LookupView):
    MODEL = Laboratory
    QUERY = "name__icontains"
    ATTRS = {'value': 'id', 'label': 'name'}


class StateLookup(View):

    def get(self, request, country_code):
        try:
            states = sorted(pycountry.subdivisions.get(
                country_code=country_code.upper()), key=lambda x: x.name)
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


class ClinitianLookup(View):

    def get(self, request):
        registry_code = request.GET['registry_code']
        all_users = CustomUser.objects.filter(registry__code=registry_code)
        filtered = [user for user in all_users if user.is_clinician and not user.is_superuser]

        json_result = []
        for clinician in filtered:
            for wg in clinician.working_groups.all():
                json_ = {}
                json_['full_name'] = "%s %s (%s)" % (
                    clinician.first_name, clinician.last_name, wg.name)
                json_['id'] = "%d_%d" % (clinician.id, wg.id)
                json_result.append(json_)

        return HttpResponse(json.dumps(json_result))


class IndexLookup(View):
    def get(self, request, reg_code):
        from rdrf.models import Registry
        from registry.patients.models import Patient
        from django.db.models import Q
        term = None
        try:
            results = []
            registry_model = Registry.objects.get(code=reg_code)
            if registry_model.has_feature("family_linkage"):
                term = request.GET.get("term", "")
                working_groups = request.user.working_groups

                query = Q(given_names__icontains=term) | Q(family_name__icontains=term)

                for patient_model in Patient.objects.filter(query):
                    if patient_model.is_index:
                        name = "%s" % patient_model
                        results.append({"code": patient_model.pk, "name": name})

        except Registry.DoesNotExist:
            results = []

        logger.debug("IndexLookup: reg code = %s term = %s results = %s" % (reg_code, term, results))

        return HttpResponse(json.dumps(results))