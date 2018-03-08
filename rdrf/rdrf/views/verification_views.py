from django.views.generic.base import View
from rdrf.models.definition.models import Registry
from registry.patients.models import Patient
from rdrf.workflows.verification import get_verifiable_cdes
from rdrf.workflows.verification import verifications_needed


from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render

class VerificationSecurityMixin:
    def security_check(self, user, registry_model):
        if not registry_model.has_feature("verification"):
            raise PermissionDenied()
        
        if not user.in_registry(registry_model):
            raise PermissionDenied()

        if not user.is_clinician:
            raise PermissionDenied()

        if not registry_model.has_feature("clinicians_have_patients"):
            raise PermissionDenied()
        
    

class PatientsRequiringVerificationView(View, VerificationSecurityMixin):
    @method_decorator(login_required)
    def get(self, request, registry_code):
        user = request.user
        registry_model = Registry.objects.get(code=registry_code)
        self.security_check(user, registry_model)
        patients_requiring_verification = [patient_model for patient_model in Patient.objects.filter(clinician=user)
                                           if len(verifications_needed(user, registry_model, patient_model)) > 0]
        context = {
            "patients": patients_requiring_verification,
        }
        
        return render(request, 'rdrf_cdes/patients_requiring_verifications.html', context)

        
class PatientVerificationView(View, VerificationSecurityMixin):
    def get(self, request, registry_code, patient_id):
        user = request.user
        registry_model = Registry.objects.get(code=registry_code)
        self.security_check(user, registry_model)
        patient_model = Patient.objects.get(id=patient_id)

        verifications = verifications_needed(user,
                                        registry_model,
                                        patient_model)

        verification_form = make_verification_form(verifications)


        context = {"verifications": verifications,
                   "form": verification_form,
                   "patient": patient_model}

        return render(request, 'rdrf_cdes/patient_verification.html', context)

    def post(self, request, registry_code, patient_id):
        form = generate_verifcation_form(request, registry_code, patient_id)
        if form.is_valid():
            self._create_annotations(form)
        else:
            pass
    
