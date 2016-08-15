from django.http import HttpResponse
from django.views.generic import View
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required

import json
import requests

from registry.groups.models import CustomUser
from registry.patients.models import Patient

from django.contrib.contenttypes.models import ContentType
from rdrf.models import RDRFContext, RDRFContextError

import pycountry

import logging
logger = logging.getLogger(__name__)


# TODO replace these views as well with Django REST framework views
class PatientLookup(View):

    @method_decorator(login_required)
    def get(self, request, reg_code):
        from rdrf.models import Registry
        from registry.patients.models import Patient
        from django.db.models import Q

        term = None
        results = []

        try:
            registry_model = Registry.objects.get(code=reg_code)
            if registry_model.has_feature("questionnaires"):
                term = request.GET.get("term", "")
                working_groups = [wg for wg in request.user.working_groups.all()]

                query = (Q(given_names__icontains=term) | Q(family_name__icontains=term)) & \
                    Q(working_groups__in=working_groups)

                for patient_model in Patient.objects.filter(query):
                    if patient_model.active:
                        name = "%s" % patient_model
                        results.append({"value": patient_model.pk, "label": name,
                                        "class": "Patient", "pk": patient_model.pk})

        except Registry.DoesNotExist:
            results = []

        return HttpResponse(json.dumps(results))


class PatientLookup(View):

    @method_decorator(login_required)
    def get(self, request, reg_code):
        from rdrf.models import Registry
        from registry.patients.models import Patient
        from registry.groups.models import WorkingGroup
        from django.db.models import Q

        term = None
        results = []

        try:
            registry_model = Registry.objects.get(code=reg_code)
            if registry_model.has_feature("questionnaires"):
                term = request.GET.get("term", "")
                if not request.user.is_superuser:
                    working_groups = [wg for wg in request.user.working_groups.all()]
                else:
                    working_groups = [wg for wg in WorkingGroup.objects.filter(registry=registry_model)]

                query = (Q(given_names__icontains=term) | Q(family_name__icontains=term)) & \
                    Q(working_groups__in=working_groups)

                for patient_model in Patient.objects.filter(query):
                    if patient_model.active:
                        name = "%s" % patient_model
                        results.append({"value": patient_model.pk, "label": name,
                                        "class": "Patient", "pk": patient_model.pk})

        except Registry.DoesNotExist:
            results = []

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
        link = reverse("patient_edit", args=[reg_code, patient.pk])
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
                relative_link = reverse("patient_edit", args=[reg_code,
                                                              patient_created.pk])
            else:
                relative_link = None

            relative_dict = {"pk": relative.pk,
                             "given_names": relative.given_names,
                             "family_name": relative.family_name,
                             "relationship": relative.relationship,
                             "class": "PatientRelative",
                             "link": relative_link}

            result["relatives"].append(relative_dict)

        return HttpResponse(json.dumps(result))

    def _get_relationships(self):
        from registry.patients.models import PatientRelative
        return [pair[0] for pair in PatientRelative.RELATIVE_TYPES]


class UsernameLookup(View):

    def get(self, request, username):
        result = {}

        try:
            CustomUser.objects.get(username=username)
            result["existing"] = True
        except CustomUser.DoesNotExist:
            result["existing"] = False

        return HttpResponse(json.dumps(result))


# TODO I think that for this one the get will be replaced by Django REST framework view
# The put that switches contexts should be moved. It isn't a lookup view for sure, but also
# it doesn't feel "right" to mix it into the REST API because it changes things in the
# session of a user that is using the web UI not consuming the API

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
        from rdrf.models import RDRFContext
        from rdrf.models import Registry
        from registry.patients.models import Patient
        user = request.user
        registry_model = Registry.objects.get(code=registry_code)
        patient_model = Patient.objects.get(pk=int(patient_id))
        desired_active_context_id = self._get_desired_active_context_id(request)
        try:
            self._set_active_context(user, registry_model, patient_model, desired_active_context_id)

        except RDRFContextError as ex:
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

    # FIXME: spurious reference to context_exception in success_packet
    def _create_success_packet(self, active_context_id):
        success_packet = {"error": context_exception.message}
        success_packet_json = json.dumps(success_packet)
        return HttpResponse(success_packet_json, status=200, content_type="application/json")


class RecaptchaValidator(View):

    def post(self, request):
        response_value = request.POST['response_value']
        secret_key = getattr(settings, "RECAPTCHA_SECRET_KEY", None)
        payload = {"secret": secret_key, "response": response_value}
        r = requests.post("https://www.google.com/recaptcha/api/siteverify", data=payload)
        return HttpResponse(r)
