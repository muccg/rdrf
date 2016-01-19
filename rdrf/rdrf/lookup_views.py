from django.http import HttpResponse
from django.views.generic import View
from django.core.urlresolvers import reverse
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required

import json

from registry.genetic.models import Gene, Laboratory
from registry.groups.models import CustomUser
from registry.patients.models import Patient

from django.contrib.contenttypes.models import ContentType
from rdrf.models import RDRFContext, RDRFContextError

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
    @method_decorator(login_required)
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
                working_groups = [wg for wg in request.user.working_groups.all()]

                query = (Q(given_names__icontains=term) | Q(family_name__icontains=term)) & \
                         Q(working_groups__in=working_groups)
                logger.debug("query = %s" % query)

                for patient_model in Patient.objects.filter(query):
                    if patient_model.is_index:
                        name = "%s" % patient_model
                        results.append({"value": patient_model.pk, "label": name, "class": "Patient", "pk": patient_model.pk })

        except Registry.DoesNotExist:
            logger.debug("reg code doesn't exist %s" % reg_code)
            results = []

        logger.debug("IndexLookup: reg code = %s term = %s results = %s" % (reg_code, term, results))

        return HttpResponse(json.dumps(results))


class FamilyLookup(View):
    @method_decorator(login_required)
    def get(self, request, reg_code, index=None):
        from rdrf.models import Registry
        result = {}
        try:
            index_patient_pk = request.GET.get("index_pk", None)
            logger.debug("index_patient_pk = %s" % index_patient_pk)
            patient = Patient.objects.get(pk=index_patient_pk)
        except Patient.DoesNotExist:
            result = {"error": "patient does not exist"}
            return HttpResponse(json.dumps(result))

        if not patient.is_index:
            result = {"error": "patient is not an index"}
            return HttpResponse(json.dumps(result))

        registry_model = Registry.objects.get(code=reg_code)
        default_context = patient.default_context(registry_model)
        assert default_context is not None
        link = reverse("patient_edit", args=[reg_code, patient.pk, default_context.pk])
        result["index"] = {"pk": patient.pk,
                           "given_names": patient.given_names,
                           "family_name": patient.family_name,
                           "class": "Patient",
                           "link": link}
        result["relatives"] = []

        relationships = self._get_relationships()
        result["relationships"] = relationships

        for relative in patient.relatives.all():
            patient_created = relative.relative_patient

            if patient_created:
                relatives_default_context = patient_created.default_context(registry_model)
                relative_link = reverse("patient_edit", args=[reg_code,
                                                              patient_created.pk,
                                                              relatives_default_context.pk])
            else:
                relative_link = None

            relative_dict = {"pk": relative.pk,
                             "given_names": relative.given_names,
                             "family_name": relative.family_name,
                             "relationship":  relative.relationship,
                             "class": "PatientRelative",
                             "link": relative_link}

            result["relatives"].append(relative_dict)


        return HttpResponse(json.dumps(result))

    def _get_relationships(self):
        from registry.patients.models import PatientRelative
        return [pair[0] for pair in PatientRelative.RELATIVE_TYPES]


class RDRFContextLookup(View):
    @method_decorator(login_required)
    def get(self, request, registry_code, patient_id):
        current_rdrf_context_id = request.session.get("rdrf_context_id", None)
        from rdrf.models import Registry
        try:
            registry_model = Registry.objects.get(code=registry_code)
            patient_type = ContentType.objects.get_for_model(Patient)
            rdrf_contexts = RDRFContext.objects.filter(registry=registry_model,
                                                       content_type=patient_type,
                                                       object_id=patient_id)

            return self.to_json(rdrf_contexts, current_rdrf_context_id)

        except Registry.DoesNotExist:
            return self.to_json([])

    def to_json(self, rdrf_contexts, current_rdrf_context_id):
        results = []
        for rdrf_context in rdrf_contexts:
            d = {}
            d["id"] = rdrf_context.pk
            d["display_name"] = rdrf_context.display_name
            d["created_at"] = rdrf_context.created_at.strftime("%d-%m-%Y")
            d["active"] = rdrf_context.pk == current_rdrf_context_id
            results.append(d)

        logger.debug("return contexts: %s" % results)

        return HttpResponse(json.dumps(results))

    @method_decorator(login_required)
    def post(self, request, registry_code, patient_id):
        """
        sent from a clinical form when user decides to switch contexts
        :param request:
        :param registry_code:
        :param patient_id:
        :return:
        """
        from rdrf.models import RDRFContext, Registry
        from registry.patients.models import Patient
        user = request.user
        registry_model = Registry.objects.get(code=registry_code)
        patient_model = Patient.objects.get(pk=int(patient_id))
        desired_active_context_id = self._get_desired_active_context_id(request)
        try:
            self._set_active_context(user, registry_model, patient_model, desired_active_context_id)

        except RDRFContextError, ex:
            # return error packet
            return self._create_error_packet(ex)

    def _get_desired_active_context_id(self, request):
        import re
        pattern = re.compile("^rdrf_context_(?P<rdrf_context_id>\d+)$")
        data = json.loads(request.body)
        rdrf_context_id_string = data["active_rdrf_context_id_string"]
        m = pattern.match(rdrf_context_id_string)
        if m:
            id_string = m.group('rdrf_context_id')
            id = int(id_string)
            return id
        else:
            return None

    def _set_active_context(self, request, registry_model, patient_model, desired_active_context_id):
        # perform some sanity checks before setting activ contexts
        if not registry_model.has_feature("contexts"):
            raise RDRFContextError("Registry %s does not support context switching" % registry_model.code)

        try:
            rdrf_context_model = RDRFContext.objects.filter(pk=desired_active_context_id)
        except RDRFContext.DoesNotExist:
            raise RDRFContextError("Selected RDRF Context %s does not exist" % desired_active_context_id)

        if rdrf_context_model.registry is not registry_model:
            raise RDRFContextError("Selected RDRF Context does not belong to registry %s" % registry_model.code)

        if rdrf_context_model.content_object is not patient_model:
            raise RDRFContextError("Selected RDRF Context does not belong to patient %s" % patient_model)

        # all ok
        request.session["rdrf_context_id"] = rdrf_context_model.pk

        return self._create_success_packet(rdrf_context_model.pk)

    def _create_error_packet(self, context_exception):
        error_packet = {"error": context_exception.message}
        error_packet_json = json.dumps(error_packet)
        return HttpResponse(error_packet_json, status=200, content_type="application/json")

    def _create_success_packet(self, active_context_id):
        success_packet = {"error": context_exception.message}
        success_packet_json = json.dumps(success_packet)
        return HttpResponse(success_packet_json, status=200, content_type="application/json")
