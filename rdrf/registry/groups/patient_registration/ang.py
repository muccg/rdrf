from base import BaseRegistration
from registry.patients.models import Patient, PatientAddress, AddressType, ParentGuardian, ClinicianOther
from registry.groups.models import WorkingGroup

from rdrf.email_notification import RdrfEmail
from django.conf import settings


class AngelmanRegistration(BaseRegistration, object):

    def __init__(self, user, request):
        super(AngelmanRegistration, self).__init__(user, request)

    def process(self,):
        registry_code = self.request.POST['registry_code']
        registry = self._get_registry_object(registry_code)
    
        user = self._create_django_user(self.request, self.user, registry, True)
    
        try:
            clinician_id, working_group_id = self.request.POST['clinician'].split("_")
            clinician = CustomUser.objects.get(id=clinician_id)
            working_group = WorkingGroup.objects.get(id=working_group_id)
            user.working_groups = [working_group, ]
        except ValueError:
            clinician = None
            working_group, status = WorkingGroup.objects.get_or_create(
                name=self._UNALLOCATED_GROUP, registry=registry)
            user.working_groups = [working_group, ]
    
        user.save()
    
        patient = Patient.objects.create(
            consent=True,
            family_name=user.last_name,
            given_names=user.first_name,
            date_of_birth=self.request.POST["date_of_birth"],
            sex=self._GENDER_CODE[self.request.POST["gender"]]
        )
    
        patient.rdrf_registry.add(registry.id)
        patient.working_groups.add(working_group.id)
        patient.clinician = clinician
        patient.home_phone = self.request.POST["phone_number"]
        patient.user = None
    
        patient.save()
        
        if "clinician-other" in self.request.POST['clinician']:
            other_clinician = ClinicianOther.objects.create(
                patient=patient,
                clinician_name=self.request.POST.get("other_clinician_name"),
                clinician_hospital=self.request.POST.get("other_clinician_hospital"),
                clinician_address=self.request.POST.get("other_clinician_address")
            )
            
        address = self._create_patient_address(patient, self.request)
        address.save()
    
        parent_guardian = self._create_parent(self.request)
        parent_guardian.patient.add(patient)
        parent_guardian.user = user
        parent_guardian.save()


    def _create_parent(self, request):
        parent_guardian = ParentGuardian.objects.create(
            first_name=request.POST["parent_guardian_first_name"],
            last_name=request.POST["parent_guardian_last_name"],
            date_of_birth=request.POST["parent_guardian_date_of_birth"],
            gender=request.POST["parent_guardian_gender"],
            address=request.POST["parent_guardian_address"],
            suburb=request.POST["parent_guardian_suburb"],
            state=request.POST["parent_guardian_state"],
            postcode=request.POST["parent_guardian_postcode"],
            country=request.POST["parent_guardian_country"],
            phone=request.POST["parent_guardian_phone"],
        )
        return parent_guardian
