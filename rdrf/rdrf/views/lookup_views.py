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

import logging
logger = logging.getLogger(__name__)


class PatientLookup(View):

    @method_decorator(login_required)
    def get(self, request, reg_code):
        from rdrf.models.definition.models import Registry
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
                    working_groups = [
                        wg for wg in WorkingGroup.objects.filter(
                            registry=registry_model)]

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

        if request.user.can_view_patient_link(patient):
            link = reverse("patient_edit", args=[reg_code, patient.pk])
            working_group = None
        else:
            link = None
            working_group = self._get_working_group_name(patient)

        result["index"] = {"pk": patient.pk,
                           "given_names": patient.given_names,
                           "family_name": patient.family_name,
                           "class": "Patient",
                           "working_group": working_group,
                           "link": link}
        result["relatives"] = []

        relationships = self._get_relationships()
        result["relationships"] = relationships

        for relative in patient.relatives.all():
            patient_created = relative.relative_patient
            working_group = None

            if patient_created:
                if request.user.can_view_patient_link(patient_created):
                    relative_link = reverse("patient_edit", args=[reg_code,
                                                                  patient_created.pk])
                else:
                    relative_link = None
                    working_group = self._get_working_group_name(patient_created)

            else:
                relative_link = None

            relative_dict = {"pk": relative.pk,
                             "given_names": relative.given_names,
                             "family_name": relative.family_name,
                             "relationship": relative.relationship,
                             "class": "PatientRelative",
                             "working_group": working_group,
                             "link": relative_link}

            result["relatives"].append(relative_dict)

        return HttpResponse(json.dumps(result))

    def _get_relationships(self):
        from registry.patients.models import PatientRelative
        return [pair[0] for pair in PatientRelative.RELATIVE_TYPES]

    def _get_working_group_name(self, patient_model):
        wgs = ",".join(sorted([wg.name for wg in patient_model.working_groups.all()]))
        return "No link - patient in " + wgs


class UsernameLookup(View):

    def get(self, request, username):
        result = {}

        try:
            CustomUser.objects.get(username=username)
            result["existing"] = True
        except CustomUser.DoesNotExist:
            result["existing"] = False

        return HttpResponse(json.dumps(result))


class RecaptchaValidator(View):

    def post(self, request):
        response_value = request.POST['response_value']
        secret_key = getattr(settings, "RECAPTCHA_SECRET_KEY", None)
        payload = {"secret": secret_key, "response": response_value}
        r = requests.post("https://www.google.com/recaptcha/api/siteverify", data=payload)
        return HttpResponse(r)
