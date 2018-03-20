from django.views.generic.base import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.template.context_processors import csrf

from rdrf.models.definition.models import Registry
from rdrf.models.definition.models import RDRFContext
from rdrf.workflows.verification import get_verifiable_cdes
from rdrf.workflows.verification import get_verifications
from rdrf.workflows.verification import VerificationStatus
from rdrf.workflows.verification import VerifiableCDE
from rdrf.workflows.verification import create_annotations

from rdrf.forms.dynamic.verification_form import make_verification_form
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
            if not patient_model.pk in [p.pk for p in Patient.objects.filter(clinician=user)]:
                raise PermissionDenied()
        
class PatientVerification:
    def __init__(self, registry_model, patient_model,context_model,verifications):
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
      
        patient_verifications =  []

        for patient_model in Patient.objects.filter(clinician=user):
            for context_model in patient_model.context_models:
                verifications = get_verifications(user, registry_model, patient_model, context_model)
                if len(verifications) > 0:
                    patient_verifications.append(PatientVerification(registry_model, patient_model,context_model,verifications))
                 
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

        verifications = get_verifications(user,
                                          registry_model,
                                          patient_model,
                                          context_model)

        form = make_verification_form(verifications)

        # We have to annotate extra properties on the field so
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
                    


        context = self._build_context(request, patient_model, form)


        return render(request, 'rdrf_cdes/patient_verification.html', context)


    def _build_context(self, request, patient_model, form, form_state="initial", errors=[]):
        options = [(VerificationStatus.UNVERIFIED, "Unverified"),
                   (VerificationStatus.VERIFIED, "Verified"),
                   (VerificationStatus.CORRECTED, "Corrected")]

        context = {
                   "location": "Patient Verification Form",
                   "form": form,
                   "form_state": form_state,
                   "errors": errors,
                   "patient": patient_model,
                   "options": options}

        context.update(csrf(request))
        return context


    @method_decorator(login_required)
    def post(self, request, registry_code, patient_id, context_id):
         # fields in the POST look like:
         #runserver_1    | [DEBUG:2018-03-13 16:45:40,339:verification_views.py:123:post] key status_AngelmanRegistryBehaviourAndDevelopment____ANGMuscleTone____ANGBEHDEVMuscleTrunk value =unverified
         #runserver_1    | [DEBUG:2018-03-13 16:45:40,339:verification_views.py:123:post] key comments_AngelmanRegistryBehaviourAndDevelopment____ANGMuscleTone____ANGBEHDEVMuscleTrunk value =
         #runserver_1    | [DEBUG:2018-03-13 16:45:40,339:verification_views.py:123:post] key status_AngelmanRegistryBehaviourAndDevelopment____ANGMuscleTone____ANGBEHDEVMuscleLimbs value =unverified
         #runserver_1    | [DEBUG:2018-03-13 16:45:40,339:verification_views.py:123:post] key comments_AngelmanRegistryBehaviourAndDevelopment____ANGMuscleTone____ANGBEHDEVMuscleLimbs value =
         #runserver_1    | [DEBUG:2018-03-13 16:45:40,340:verification_views.py:123:post] key status_AngelmanRegistryEpilepsy____ANGFebrileEpilepsy____ANGEpilepsyCease value =corrected
         #runserver_1    | [DEBUG:2018-03-13 16:45:40,340:verification_views.py:123:post] key AngelmanRegistryEpilepsy____ANGFebrileEpilepsy____ANGEpilepsyCease value =7
         #runserver_1    | [DEBUG:2018-03-13 16:45:40,340:verification_views.py:123:post] key comments_AngelmanRegistryEpilepsy____ANGFebrileEpilepsy____ANGEpilepsyCease value =
         #runserver_1    | [DEBUG:2018-03-13 16:45:40,340:verification_views.py:123:post] key status_AngelmanRegistryEpilepsy____ANGFebrileEpilepsy____ANGSeizureFrequencyAFebrile value =verified
         #runserver_1    | [DEBUG:2018-03-13 16:45:40,340:verification_views.py:123:post] key comments_AngelmanRegistryEpilepsy____ANGFebrileEpilepsy____ANGSeizureFrequencyAFebrile value =low

        user = request.user
        registry_model = Registry.objects.get(code=registry_code)
        patient_model = Patient.objects.get(pk=patient_id)
        context_model = RDRFContext.objects.get(id=context_id)
        self.security_check(user, registry_model, patient_model)

        # these are the verfications entered
        verification_map = self._get_verification_map(request, registry_code)

        corrected = [v for v in verification_map.values() if v.status == VerificationStatus.CORRECTED]
        verified = [v for v in verification_map.values() if v.status == VerificationStatus.VERIFIED]
        
        form = make_verification_form(corrected)

        if len(corrected) == 0 or form.is_valid():
            form_state = "valid"
            errors = []
            create_annotations(request.user,
                               registry_model,
                               patient_model,
                               context_model,
                               verified=verified,
                               corrected=corrected)
            
        else:
            form_state = "invalid"
            raise Exception(form)
            errors = [e for e in form.errors]
            logger.debug("errors = %s" % errors)
            

        context = self._build_context(request, patient_model, form, form_state, errors)
        return render(request, 'rdrf_cdes/patient_verification.html', context)

    def _get_verification_map(self, request, registry_code):
        from rdrf.helpers.utils import models_from_mongo_key
        registry_model = Registry.objects.get(code=registry_code)
        verifications = []
        verification_map = {}

        def mk_ver(delimited_key):
            form_model, section_model,cde_model = models_from_mongo_key(registry_model,delimited_key)
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
                    
                    
                
                
         
                    

                    
                    

                
