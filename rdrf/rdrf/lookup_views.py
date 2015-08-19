from django.http import HttpResponse
from django.views.generic import View
from django.core.urlresolvers import reverse
import json

from registry.genetic.models import Gene, Laboratory
from registry.groups.models import CustomUser
from registry.patients.models import Patient

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
        results = []
        try:
            registry_model = Registry.objects.get(code=reg_code)
            if registry_model.has_feature("family_linkage"):
                term = request.GET.get("term", "")
                working_groups = request.user.working_groups

                query = Q(given_names__icontains=term) | Q(family_name__icontains=term)
                logger.debug("query = %s" % query)

                for patient_model in Patient.objects.filter(query):
                    if patient_model.is_index:
                        name = "%s" % patient_model
                        results.append({"value": patient_model.pk, "label": name})

        except Registry.DoesNotExist:
            logger.debug("reg code doesn't exist %s" % reg_code)
            results = []

        logger.debug("IndexLookup: reg code = %s term = %s results = %s" % (reg_code, term, results))

        return HttpResponse(json.dumps(results))


class FamilyLookup(View):
    def get(self, request, reg_code):
        result = {}
        try:
            index_patient_pk = request.GET.get("index_pk", None)
            patient = Patient.objects.get(pk=index_patient_pk)
        except Patient.DoesNotExist:
            result = {"error": "patient does not exist"}
            return HttpResponse(json.dumps(result))

        if not patient.is_index:
            result = {"error": "patient is not an index"}
            return HttpResponse(json.dumps(result))

        link = reverse("patient_edit", args=[reg_code, patient.pk])
        result["index"] = {"pk": patient.pk,
                           "given_names": patient.given_names,
                           "family_name": patient.family_name,
                           "link": link}
        result["relatives"] = []

        relationships = self._get_relationships()
        result["relationships"] = relationships

        for relative in patient.relatives.all():
            patient_created = relative.relative_patient

            if patient_created:
                relative_link = reverse("patient_edit", args=[reg_code, patient_created.pk])
            else:
                relative_link = None

            relative_dict = {"pk": relative.pk,
                             "given_names": relative.given_names,
                             "family_name": relative.family_name,
                             "relationship":  relative.relationship,
                             "link": relative_link}

            result["relatives"].append(relative_dict)


        return HttpResponse(json.dumps(result))

    def _get_relationships(self):
        from registry.patients.models import PatientRelative
        return [pair[0] for pair in PatientRelative.RELATIVE_TYPES]





