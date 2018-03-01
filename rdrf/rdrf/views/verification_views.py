from django.views.generic.base import View
from rdrf.models.definition.models import Registry
from registry.patients.models import Patient
from rdrf.workflows.verification import get_verifiable_cdes, VerificatonState

from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


class PatientsRequiringVerifcationView(View):
    @method_decorator(login_required)
    def get(self, request, registry_code):
        user = request.user
        registry_model = Registry.objects.get(code=registry_code)

        if not registry_model.has_feature("verification"):
            raise PermissionDenied()
        
        if not user.in_registry(registry_model):
            raise PermissionDenied()

        if not user.is_clinician():
            raise PermissionDenied()

        if not registry_model.has_feature("clinicians_have_patients"):
            raise PermissionDenied()


        verifications_required = get_verifiable_cdes(registry_model)

            

        

        
        
