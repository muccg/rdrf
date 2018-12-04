from django.views.generic.base import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.core.urlresolvers import reverse
from django.template.context_processors import csrf
from django.contrib import messages

from rdrf.models.definition.models import Registry
from rdrf.models.definition.models import RDRFContext
from rdrf.workflows.verification import get_verifications
from rdrf.workflows.verification import VerificationStatus
from rdrf.workflows.verification import VerifiableCDE
from rdrf.workflows.verification import create_annotations
from rdrf.workflows.verification import send_participant_notification
from rdrf.workflows.verification import get_diagnosis

from rdrf.forms.dynamic.verification_form import make_verification_form
from rdrf.forms.navigation.locators import PatientLocator
from registry.patients.models import Patient

import logging

logger = logging.getLogger(__name__)

class VerificationSecurityMixin:
    def security_check(self, user, registry_model, patient_model=None):
        if not registry_model.has_feature("verification"):
            raise PermissionDenied()

        if not user.in_registry(registry_model):
            raise PermissionDenied()

        if not user.is_clinician:
            raise PermissionDenied()

        if not registry_model.has_feature("clinicians_have_patients"):
            raise PermissionDenied()

        if patient_model is not None:
            if patient_model.pk not in [p.pk for p in Patient.objects.filter(clinician=user)]:
                raise PermissionDenied()

class PatientVerification:
    def __init__(self, user, registry_model, patient_model, context_model, verifications):
        self.user = user
        self.registry_model = registry_model
        self.patient_model = patient_model
        self.context_model = context_model
        self.verifications = verifications

    @property
    def title(self):
        return "%s" % self.patient_model

    @property
    def number(self):
        return len(self.verifications)

    def _get_annotations(self, status):
        def annotation_check(v, exists=True):
            p = v.has_annotation(self.user,
                                 self.registry_model,
                                 self.patient_model,
                                 self.context_model)
            if exists:
                return p
            else:
                return not p

        if status == "unverified":
            return [v for v in self.verifications if annotation_check(v, exists=False)]

        verifications_with_annotations = [v for v in self.verifications if annotation_check(v)]

        return [v for v in verifications_with_annotations if v.status == status]

    @property
    def number_unverified(self):
        return len(self._get_annotations("unverified"))

    @property
    def number_verified(self):
        return len(self._get_annotations("verified"))

    @property
    def number_corrected(self):
        return len(self._get_annotations("corrected"))

    @property
    def link(self):
        return reverse("patient_verification", args=[self.registry_model.code,
                                                     self.patient_model.pk,
                                                     self.context_model.pk])

class PatientsRequiringVerificationView(View, VerificationSecurityMixin):
    @method_decorator(login_required)
    def get(self, request, registry_code):
        user = request.user
        registry_model = Registry.objects.get(code=registry_code)
        self.security_check(user, registry_model)

        patient_verifications = []

        for patient_model in Patient.objects.filter(clinician=user):
            for context_model in patient_model.context_models:
                verifications = get_verifications(user, registry_model, patient_model, context_model)
                if len(verifications) > 0:
                    patient_verifications.append(PatientVerification(user,
                                                                     registry_model,
                                                                     patient_model,
                                                                     context_model,
                                                                     verifications))

        context = {
            "location": "Clinician Verification",
            "patient_verifications": patient_verifications,
        }

        return render(request, 'rdrf_cdes/patients_requiring_verifications.html', context)


class PatientVerificationView(View, VerificationSecurityMixin):
    @method_decorator(login_required)
    def get(self, request, registry_code, patient_id, context_id):
        user = request.user
        registry_model = Registry.objects.get(code=registry_code)
        patient_model = Patient.objects.get(id=patient_id)
        context_model = RDRFContext.objects.get(id=context_id)

        self.security_check(user, registry_model, patient_model)

        verifications = self._sort_verifications(get_verifications(user,
                                                                   registry_model,
                                                                   patient_model,
                                                                   context_model))
        form = make_verification_form(verifications)
        form = self._wrap_form(patient_model, context_model, form, verifications)
        context = self._build_context(request, registry_model, patient_model, form)

        return render(request, 'rdrf_cdes/patient_verification.html', context)

    def _sort_verifications(self, verifications):
        return sorted(verifications, key=lambda v: v.position)

    def _wrap_form(self, patient_model, context_model, form, verifications):
        # We have to annotate extra properties on the fields so
        # So we show the patient answer also
        for field in form:
            form_name, section_code, cde_code = field.name.split("____")
            logger.debug("checking cde %s" % cde_code)
            for v in verifications:
                if all([v.form_model.name == form_name,
                        v.section_model.code == section_code,
                        v.cde_model.code == cde_code]):

                    # display value
                    logger.debug("adding extra properties to field for template")

                    field.patient_answer = v.get_data(patient_model, context_model)
                    logger.debug("patient display value = %s" % field.patient_answer)
                    # non display value , used in hidden field
                    field.patient_data = v.patient_data
                    field.status = v.status
                    logger.debug("field status = %s" % field.status)
                    field.comments = v.comments
                    logger.debug("field comments = %s" % field.comments)
        return form

    def _build_context(self, request, registry_model, patient_model, form, form_state="initial", errors=[]):
        options = [(VerificationStatus.UNVERIFIED, "Unverified"),
                   (VerificationStatus.VERIFIED, "Verified"),
                   (VerificationStatus.CORRECTED, "Corrected")]

        patient_locator = PatientLocator(registry_model,
                                         patient_model)

        demographics_link = patient_locator.get_link()

        context = {
            "location": "Patient Verification Form",
            "form": form,
            "demographics_link": demographics_link,
            "form_state": form_state,
            "errors": errors,
            "patient": patient_model,
            "options": options}

        context.update(csrf(request))
        return context

    @method_decorator(login_required)
    def post(self, request, registry_code, patient_id, context_id):
        user = request.user
        registry_model = Registry.objects.get(code=registry_code)
        patient_model = Patient.objects.get(pk=patient_id)
        context_model = RDRFContext.objects.get(id=context_id)
        self.security_check(user, registry_model, patient_model)
        # these are the verifications posted in the form
        verification_map = self._get_verification_map(request, registry_code)

        # these are the corrections to the patient responses from the clinician which are new edited values
        # that require validation
        # if there are no corrections there is no need to validate
        corrected = [v for v in verification_map.values() if v.status == VerificationStatus.CORRECTED]
        # these are the fields which are deemed to be ok ( patient response is good)
        verified = [v for v in verification_map.values() if v.status == VerificationStatus.VERIFIED]
        # fields which are unknown
        unverified = [v for v in verification_map.values() if v.status == VerificationStatus.UNVERIFIED]
        # this are used to
        verifications = self._sort_verifications(corrected + verified + unverified)

        form = make_verification_form(corrected)

        if len(corrected) == 0 or form.is_valid():
            form_state = "valid"
            errors = []
            create_annotations(user,
                               registry_model,
                               patient_model,
                               context_model,
                               verified=verified,
                               corrected=corrected)
            # we need to re-present the full form to the user
            # we need diagnosis
            diagnosis = get_diagnosis(registry_model, verifications)
            send_participant_notification(registry_model, user, patient_model, diagnosis)
            form = make_verification_form(verifications)
            form = self._wrap_form(patient_model, context_model, form, verifications)
            messages.add_message(request, messages.SUCCESS, "Form saved successfully")
            context = self._build_context(request, registry_model, patient_model, form)
        else:
            form_state = "invalid"
            errors = [e for e in form.errors]
            form = make_verification_form(verifications)
            form = self._wrap_form(patient_model, context_model, form, verifications)
            messages.add_message(request, messages.ERROR, "Form not saved due to error(s)")
            context = self._build_context(request, registry_model, patient_model, form, errors=errors)

        return render(request, 'rdrf_cdes/patient_verification.html', context)

    def _get_verification_map(self, request, registry_code):
         # fields in the POST look like:
         # runserver_1    | [DEBUG:2018-03-13 16:45:40,339:verification_views.py:123:post] key status_AngelmanRegistryBehaviourAndDevelopment____ANGMuscleTone____ANGBEHDEVMuscleTrunk value =unverified
         # runserver_1    | [DEBUG:2018-03-13 16:45:40,339:verification_views.py:123:post] key comments_AngelmanRegistryBehaviourAndDevelopment____ANGMuscleTone____ANGBEHDEVMuscleTrunk value =
         # runserver_1    | [DEBUG:2018-03-13 16:45:40,339:verification_views.py:123:post] key status_AngelmanRegistryBehaviourAndDevelopment____ANGMuscleTone____ANGBEHDEVMuscleLimbs value =unverified
         # runserver_1    | [DEBUG:2018-03-13 16:45:40,339:verification_views.py:123:post] key comments_AngelmanRegistryBehaviourAndDevelopment____ANGMuscleTone____ANGBEHDEVMuscleLimbs value =
         # runserver_1    | [DEBUG:2018-03-13 16:45:40,340:verification_views.py:123:post] key status_AngelmanRegistryEpilepsy____ANGFebrileEpilepsy____ANGEpilepsyCease value =corrected
         # runserver_1    | [DEBUG:2018-03-13 16:45:40,340:verification_views.py:123:post] key AngelmanRegistryEpilepsy____ANGFebrileEpilepsy____ANGEpilepsyCease value =7
         # runserver_1    | [DEBUG:2018-03-13 16:45:40,340:verification_views.py:123:post] key comments_AngelmanRegistryEpilepsy____ANGFebrileEpilepsy____ANGEpilepsyCease value =
         # runserver_1    | [DEBUG:2018-03-13 16:45:40,340:verification_views.py:123:post] key status_AngelmanRegistryEpilepsy____ANGFebrileEpilepsy____ANGSeizureFrequencyAFebrile value =verified
         # runserver_1    | [DEBUG:2018-03-13 16:45:40,340:verification_views.py:123:post] key comments_AngelmanRegistryEpilepsy____ANGFebrileEpilepsy____ANGSeizureFrequencyAFebrile value =low
        from rdrf.helpers.utils import models_from_mongo_key
        registry_model = Registry.objects.get(code=registry_code)
        verifications = []
        verification_map = {}

        def mk_ver(delimited_key):
            form_model, section_model, cde_model = models_from_mongo_key(registry_model, delimited_key)
            v = VerifiableCDE(registry_model,
                              form_model=form_model,
                              section_model=section_model,
                              cde_model=cde_model)
            return v

        for key in request.POST:
            if key.startswith("status_"):
                status = request.POST[key]
                delimited_key = key[7:]
                if delimited_key in verification_map:
                    verification_map[delimited_key].status = status
                else:
                    v = mk_ver(delimited_key)
                    v.status = status
                    verification_map[delimited_key] = v
            elif key.startswith("comments_"):
                comments = request.POST[key]
                delimited_key = key[9:]
                if delimited_key in verification_map:
                    verification_map[delimited_key].comments = comments
                else:
                    v = mk_ver(delimited_key)
                    v.comments = comments
                    verification_map[delimited_key] = v
            elif key.startswith("patient_data_"):
                # this is the patient data that needs to be verified
                patient_data = request.POST[key]
                delimited_key = key[13:]
                if delimited_key in verification_map:
                    verification_map[delimited_key].patient_data = patient_data
                else:
                    v = mk_ver(delimited_key)
                    v.patient_data = patient_data
                    verification_map[delimited_key] = v

            elif key.startswith("pos_"):
                position = int(request.POST[key])
                delimited_key = key[4:]
                if delimited_key in verification_map:
                    verification_map[delimited_key].position = position
                else:
                    v = mk_ver(delimited_key)
                    v.position = position
                    verification_map[delimited_key] = v
            elif "____" in key:
                # new value from clinician  if there is one
                field_value = request.POST[key]
                if key in verification_map:
                    verification_map[key].set_clinician_value(field_value)
                else:
                    v = mk_ver(key)
                    v.set_clinician_value(field_value)
                    verification_map[key] = v

        return verification_map
