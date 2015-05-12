from django.contrib.auth.models import User as AuthUser
from django.contrib.auth.models import Group
from django.contrib.auth.models import AbstractUser, BaseUserManager

from django.db.models.signals import post_save
from django.db import models, transaction

from django.dispatch import receiver
from django.dispatch import receiver

from registration.signals import user_registered

from rdrf.models import Registry

_OTHER_CLINICIAN = "clinician-other"
_UNALLOCATED_GROUP = "Unallocated"

class WorkingGroup(models.Model):
    name = models.CharField(max_length=100)
    registry = models.ForeignKey(Registry, null=True)

    class Meta:
        ordering = ["name"]

    def __unicode__(self):
        return self.name


class CustomUser(AbstractUser):
    working_groups = models.ManyToManyField(WorkingGroup, null=True, related_name = 'working_groups')
    title = models.CharField(max_length=50, null=True, verbose_name="position")
    registry = models.ManyToManyField(Registry, null=False, blank=False, related_name='registry')

    @property
    def num_registries(self):
        return self.registry.count()

    def can(self, verb, datum):
        if verb == "see":
            return any([ registry.shows(datum) for registry in self.registry.all() ])

    @property
    def notices(self):
        from rdrf.models import Notification
        return Notification.objects.filter(to_username=self.username, seen=False).order_by("-created")

    def in_registry(self, registry_model):
        for reg in self.registry.all():
            if reg is registry_model:
                return True

    @property
    def is_patient(self):
        try:
            patient_group = Group.objects.get(name__icontains="patients")
            _is_patient = True if patient_group in self.groups.all() else False
            return _is_patient
        except Group.DoesNotExist:
            return False

    @property
    def is_clinician(self):
        try:
            clinical_group = Group.objects.get(name__icontains="clinical")
            _is_clinicial = True if clinical_group in self.groups.all() else False
            return _is_clinicial
        except Group.DoesNotExist:
            return False

    @property
    def is_genetic_staff(self):
        try:
            genetic_staff_group = Group.objects.get(name__icontains="genetic staff")
            _is_genetic = True if genetic_staff_group in self.groups.all() else False
            return _is_genetic
        except Group.DoesNotExist:
            return False

    @property
    def is_genetic_curator(self):
        try:
            genetic_curator_group = Group.objects.get(name__icontains="genetic curator")
            _is_genetic = True if genetic_curator_group in self.groups.all() else False
            return _is_genetic
        except Group.DoesNotExist:
            return False

    @property
    def is_working_group_staff(self):
        try:
            g = Group.objects.get(name__icontains="working group staff")
            t = True if g in self.groups.all() else False
            return t
        except Group.DoesNotExist:
            return False

    @property
    def is_curator(self):
        try:
            curator_group = Group.objects.get(name__icontains="working group curator")
            _is_curator = True if curator_group in self.groups.all() else False
            return _is_curator
        except Group.DoesNotExist:
            return False

    def get_groups(self):
        return self.groups.all()

    def get_working_groups(self):
        return self.working_groups.all()

    def get_registries(self):
        return self.registry.all()

    def can_view(self, registry_form_model):
        if self.is_superuser:
            return True

        form_registry = registry_form_model.registry
        my_registries = [ r for r in self.registry.all()]

        if form_registry not in my_registries:
            return False

        if registry_form_model.open:
            return True

        form_allowed_groups = [g for g in registry_form_model.groups_allowed.all()]

        for group in self.groups.all():
            if group in form_allowed_groups:
                return True

        return False
    
@receiver(user_registered) 
def user_registered_callback(sender, user, request, **kwargs):
    from registry.patients.models import Patient, PatientAddress, AddressType, ParentGuardian

    user.first_name = request.POST['first_name']
    user.last_name = request.POST['surname']
    user.is_staff = True
    
    patient_group = _get_group("Patients")
    user.groups = [ patient_group, ] if patient_group else []
    
    registry_code = request.POST['registry_code']
    registry = _get_registry_object(registry_code)
    user.registry = [ registry, ] if registry else []

    try:    
        clinician_id, working_group_id = request.POST['clinician'].split("_")
        clinician = CustomUser.objects.get(id=clinician_id)
        working_group = WorkingGroup.objects.get(id=working_group_id)
        user.working_groups = [ working_group, ]
    except ValueError:
        clinician = None
        working_group, status = WorkingGroup.objects.get_or_create(name=_UNALLOCATED_GROUP)
        user.working_groups = [ working_group, ]
    
    user.save()

    patient = Patient.objects.create(
        consent=True,
        family_name = user.last_name,
        given_names = user.first_name,
        date_of_birth = request.POST["date_of_birth"],
        sex = request.POST["gender"]
    )

    patient.rdrf_registry.add(registry.id)
    patient.working_groups.add(working_group.id)
    patient.clinician = clinician
    patient.home_phone = getattr(request.POST, "phone_number", None)
    patient.user = user
    patient.save()
    
    addres = PatientAddress.objects.create(
        patient = patient,
        address_type = AddressType.objects.get(description__icontains = "Post"),
        address = request.POST["address"],
        suburb = request.POST["suburb"],
        state = request.POST["state"],
        postcode = request.POST["postcode"],
        country = request.POST["country"]
    ).save()

    if request.POST.has_key("parent_guardian_check"):
        parent_guardian = ParentGuardian.objects.create(
            first_name = request.POST["parent_guardian_first_name"],
            last_name = request.POST["parent_guardian_last_name"],
            date_of_birth = request.POST["parent_guardian_date_of_birth"],
            gender = request.POST["parent_guardian_gender"],
            address = request.POST["parent_guardian_address"],
            suburb = request.POST["parent_guardian_suburb"],
            state = request.POST["parent_guardian_state"],
            postcode = request.POST["parent_guardian_postcode"],
            country = request.POST["parent_guardian_country"]
        )
        parent_guardian.patient.add(patient)
        parent_guardian.save()


def _get_registry_object(registry_name):
    try:
        registry = Registry.objects.get(code__iexact = registry_name)
        return registry
    except Registry.DoesNotExist:
        return None
    
def _get_group(group_name):
    try:
        group = Group.objects.get(name__icontains = group_name)
        return group
    except Group.DoesNotExist:
        return None
