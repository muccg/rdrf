import abc

from rdrf.models.definition.models import Registry
from registry.patients.models import PatientAddress, AddressType
from registry.patients.models import ParentGuardian
from django.contrib.auth.models import Group
from django.utils.translation import get_language

import logging

logger = logging.getLogger(__name__)


class BaseRegistration(object):

    _OTHER_CLINICIAN = "clinician-other"
    _UNALLOCATED_GROUP = "Unallocated"

    _ADDRESS_TYPE = "Postal"
    _GENDER_CODE = {
        "M": 1,
        "F": 2,
        "I": 3
    }

    _TRUE_FALSE = {
        'true': True,
        'false': False
    }

    user = None
    request = None

    def __init__(self, user, request):
        self.user = user
        self.request = request

    @abc.abstractmethod
    def process(self, ):
        return

    def _create_django_user(self, request, django_user, registry, is_parent, groups=[], is_clinician=False):
        user_groups = [self._get_group(g) for g in groups]
        if not user_groups:
            if is_parent:
                user_group = self._get_group("Parents")
            elif is_clinician:
                user_group = self._get_group("Clinical Staff")
            else:
                user_group = self._get_group("Patients")
            django_user.groups.set([user_group.id, ] if user_group else [])
        else:
            django_user.groups.set([g.id for g in user_groups])

        if is_parent:
            django_user.first_name = request.POST['parent_guardian_first_name']
            django_user.last_name = request.POST['parent_guardian_last_name']
        elif is_clinician:
            # clinician signup only exists on subclass ..
            django_user.first_name = self.clinician_signup.clinician_other.clinician_first_name
            django_user.last_name = self.clinician_signup.clinician_other.clinician_last_name
        else:
            django_user.first_name = request.POST['first_name']
            django_user.last_name = request.POST['surname']
        django_user.registry.set([registry, ] if registry else [])
        django_user.is_staff = True
        return django_user

    def _create_patient_address(self, patient, request, address_type="Postal"):
        address = PatientAddress.objects.create(
            patient=patient,
            address_type=self.get_address_type(address_type),
            address=request.POST["address"],
            suburb=request.POST["suburb"],
            state=request.POST["state"],
            postcode=request.POST["postcode"],
            country=request.POST["country"]
        )
        return address

    @property
    def language(self):
        return get_language()

    def _create_parent(self, request):
        parent_guardian = ParentGuardian.objects.create(
            first_name=request.POST["parent_guardian_first_name"],
            last_name=request.POST["parent_guardian_last_name"],
            date_of_birth=request.POST["parent_guardian_date_of_birth"],
            gender=self._GENDER_CODE[request.POST["parent_guardian_gender"]],
            address=request.POST["parent_guardian_address"],
            suburb=request.POST["parent_guardian_suburb"],
            state=request.POST["parent_guardian_state"],
            postcode=request.POST["parent_guardian_postcode"],
            country=request.POST["parent_guardian_country"],
            phone=request.POST["parent_guardian_phone"],
        )
        return parent_guardian

    def _get_registry_object(self, registry_name):
        try:
            registry = Registry.objects.get(code__iexact=registry_name)
            return registry
        except Registry.DoesNotExist:
            return None

    def _get_group(self, group_name):
        try:
            group, created = Group.objects.get_or_create(name=group_name)
            return group
        except Group.DoesNotExist:
            return None

    def get_address_type(self, address_type):
        address_type_obj, created = AddressType.objects.get_or_create(type=address_type)
        return address_type_obj
