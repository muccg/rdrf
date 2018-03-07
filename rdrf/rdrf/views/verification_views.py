from django.views.generic.base import View
from rdrf.models.definition.models import Registry
from registry.patients.models import Patient
from rdrf.workflows.verification import get_verifiable_cdes, VerificatonState

from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render

class VerificationMixin:
    def security_check(user, registry_model):
        if not registry_model.has_feature("verification"):
            raise PermissionDenied()
        
        if not user.in_registry(registry_model):
            raise PermissionDenied()

        if not user.is_clinician():
            raise PermissionDenied()

        if not registry_model.has_feature("clinicians_have_patients"):
            raise PermissionDenied()
        
    

class PatientsRequiringVerifcationView(View, VerificationMixin):
    @method_decorator(login_required)
    def get(self, request, registry_code):
        user = request.user
        registry_model = Registry.objects.get(code=registry_code)
        self.security_check(user, registry_model)
        patients_requiring_verification = [p for p in Patient.objects.filter(clinician=user)
                                           if len(verifications_needed(user, registry_model, patient_model)) > 0]
        context = {
            "patients": patients_requiring_verification,
        }
        
        return render(request, 'rdrf_cdes/patients_verification_view.html', context)

        
class PatientVerificationView(View, VerficationMixin):
    def get(self, request, registry_code, patient_id):
        user = request.user
        registry_model = Registry.objects.get(code=registry_code)
        self.security_check(user, registry_model)
        patient_model = Patient.objects.get(id=patient_id)

        verifications = verifications_needed(user,
                                        registry_model,
                                        patient_model)


        context = {"verifications": verifications,
                   "patient": patient_model}

        return render(request, 'rdrf_cdes/patient_verification_view.html', context)
