from base import BaseRegistration
from rdrf.email_notification import process_notification
from registration.models import RegistrationProfile

from registry.groups.models import WorkingGroup
from registry.patients.models import Patient, PatientAddress, AddressType, ParentGuardian, ClinicianOther
from django.conf import settings


class FkrpRegistration(BaseRegistration, object):

    def __init__(self, user, request):
        super(FkrpRegistration, self).__init__(user, request)

    def process(self,):
        is_parent = True if self._TRUE_FALSE[self.request.POST['is_parent']] else False
        self_patient = True if self._TRUE_FALSE[self.request.POST['self_patient']] else False
    
        registry_code = self.request.POST['registry_code']
        registry = self._get_registry_object(registry_code)
    
        user = self._create_django_user(self.request, self.user, registry, is_parent)
    
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
        patient.home_phone = getattr(self.request.POST, "phone_number", None)
        patient.user = None if is_parent else user
    
        patient.save()
        
        if "clinician-other" in self.request.POST['clinician']:
            ClinicianOther.objects.create(
                patient=patient,
                clinician_name=self.request.POST.get("other_clinician_name"),
                clinician_hospital=self.request.POST.get("other_clinician_hospital"),
                clinician_address=self.request.POST.get("other_clinician_address")
            )
            template_data = {
                "other_clinician": other_clinician,
                "patient": patient
            }
            process_notification(registry_code, settings.EMAIL_NOTE_OTHER_CLINICIAN, self.request.LANGUAGE_CODE, template_data)
            
        address = self._create_patient_address(patient, self.request)
        address.save()
    
        if is_parent:
            parent_guardian = self._create_parent(self.request)
            parent_guardian.patient.add(patient)
            parent_guardian.user = user
            parent_guardian.save()
        
        if self_patient:
            parent_self_patient = Patient.objects.create(
                consent=True,
                family_name=self.request.POST["parent_guardian_last_name"],
                given_names=self.request.POST["parent_guardian_first_name"],
                date_of_birth=self.request.POST["parent_guardian_date_of_birth"],
                sex=self._GENDER_CODE[self.request.POST["parent_guardian_gender"]],
            )
            
            PatientAddress.objects.create(
                patient=parent_self_patient,
                address_type=AddressType.objects.get(description__icontains=self._ADDRESS_TYPE),
                address=self.request.POST["parent_guardian_address"],
                suburb=self.request.POST["parent_guardian_suburb"],
                state=self.request.POST["parent_guardian_state"],
                postcode=self.request.POST["parent_guardian_postcode"],
                country=self.request.POST["parent_guardian_country"]
            )
            
            parent_self_patient.rdrf_registry.add(registry)
            parent_self_patient.clinician = patient.clinician
            parent_self_patient.save()
            
            parent_guardian.patient.add(parent_self_patient)
            parent_guardian.self_patient = parent_self_patient
            parent_guardian.save()
        
        template_data = {
            "patient": patient,
            "registration": RegistrationProfile.objects.get(user=user)
        }
        process_notification(registry_code, settings.EMAIL_NOTE_NEW_PATIENT, self.request.LANGUAGE_CODE, template_data)
