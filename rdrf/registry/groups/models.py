import re

from django.core import validators

from django.contrib.auth.models import User as AuthUser
from django.contrib.auth.models import Group
from django.contrib.auth.models import AbstractBaseUser, UserManager, PermissionsMixin

from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

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
        ordering = ["registry__code"]

    def __unicode__(self):
        if self.registry:
            return "%s %s" % (self.registry.code, self.name)
        else:
            return self.name

    @property
    def display_name(self):
        if self.registry:
            return "%s %s" % (self.registry.code, self.name)
        else:
            return self.name


class CustomUser(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(_('username'), max_length=254, unique=True,
        help_text=_('Required. 254 characters or fewer. Letters, numbers and @/./+/-/_ characters'),
        validators=[
            validators.RegexValidator(re.compile('^[\w.@+-]+$'), _('Enter a valid username.'), _('invalid'))
        ])
    first_name = models.CharField(_('first name'), max_length=30)
    last_name = models.CharField(_('last name'), max_length=30)
    email = models.EmailField(_('email address'), max_length=254)
    is_staff = models.BooleanField(_('staff status'), default=False,
        help_text=_('Designates whether the user can log into this admin site.'))
    is_active = models.BooleanField(_('active'), default=False,
        help_text=_('Designates whether this user should be treated as active. Unselect this instead of deleting accounts.'))
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)
    
    working_groups = models.ManyToManyField(WorkingGroup, related_name='working_groups')
    title = models.CharField(max_length=50, null=True, verbose_name="position")
    registry = models.ManyToManyField(Registry, null=False, blank=False, related_name='registry')
    
    USERNAME_FIELD = "username"
    
    objects = UserManager()
    
    def get_full_name(self):
        full_name = "%s %s" % (self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        return self.first_name

    @property
    def num_registries(self):
        return self.registry.count()

    def can(self, verb, datum):
        if verb == "see":
            return any([registry.shows(datum) for registry in self.registry.all()])

    @property
    def notices(self):
        from rdrf.models import Notification
        return Notification.objects.filter(
            to_username=self.username,
            seen=False).order_by("-created")

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
    def is_parent(self):
        try:
            parent_group = Group.objects.get(name__icontains="parents")
            _is_parent = True if parent_group in self.groups.all() else False
            return _is_parent
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

    def has_feature(self, feature):
        if not self.is_superuser:
            return any([r.has_feature(feature) for r in self.registry.all()])
        else:
            return any([r.has_feature(feature) for r in Registry.objects.all()])

    def can_view(self, registry_form_model):
        if self.is_superuser:
            return True

        form_registry = registry_form_model.registry
        my_registries = [r for r in self.registry.all()]

        if form_registry not in my_registries:
            return False

        if registry_form_model.open:
            return True

        form_allowed_groups = [g for g in registry_form_model.groups_allowed.all()]

        for group in self.groups.all():
            if group in form_allowed_groups:
                return True

        return False

    @property
    def quick_links(self):
        from rdrf.quick_links import QuickLinks
        if self.is_superuser:
            links = QuickLinks.ALL
        elif self.is_curator:
            links = QuickLinks.WORKING_GROUP_CURATORS
        elif self.is_clinician:
            links = QuickLinks.CLINICIAN
        elif self.is_patient:
            return []
        elif self.is_genetic_curator:
            links = QuickLinks.GENETIC_CURATORS
        elif self.is_genetic_staff:
            return QuickLinks.GENETIC_STAFF
        elif self.is_working_group_staff:
            links = QuickLinks.WORKING_GROUP_STAFF
        else:
            links = []

        if not self.has_feature("questionnaires"):
            links = links - QuickLinks.QUESTIONNAIRE_HANDLING

        if self.has_feature("family_linkage"):
            links = links | QuickLinks.DOCTORS

        return links

CustomUser._meta.get_field('username')._unique = False

@receiver(user_registered)
def user_registered_callback(sender, user, request, **kwargs):
    from registry.patients.models import Patient, PatientAddress, AddressType, ParentGuardian, ClinicianOther

    is_parent = "parent_guardian_check" in request.POST

    registry_code = request.POST['registry_code']
    registry = _get_registry_object(registry_code)

    user = _create_django_user(request, user, registry, is_parent)

    try:
        clinician_id, working_group_id = request.POST['clinician'].split("_")
        clinician = CustomUser.objects.get(id=clinician_id)
        working_group = WorkingGroup.objects.get(id=working_group_id)
        user.working_groups = [working_group, ]
    except ValueError:
        clinician = None
        working_group, status = WorkingGroup.objects.get_or_create(
            name=_UNALLOCATED_GROUP, registry=registry)
        user.working_groups = [working_group, ]

    user.save()

    patient = Patient.objects.create(
        consent=True,
        family_name=user.last_name,
        given_names=user.first_name,
        date_of_birth=request.POST["date_of_birth"],
        sex=request.POST["gender"]
    )

    patient.rdrf_registry.add(registry.id)
    patient.working_groups.add(working_group.id)
    patient.clinician = clinician
    patient.home_phone = getattr(request.POST, "phone_number", None)
    patient.user = None if is_parent else user

    patient.save()
    
    if "clinician-other" in request.POST['clinician']:
        ClinicianOther.objects.create(
            patient=patient,
            clinician_name=request.POST.get("other_clinician_name"),
            clinician_hospital=request.POST.get("other_clinician_hospital"),
            clinician_address=request.POST.get("other_clinician_address")
        )


    address = _create_patient_address(patient, request)
    address.save()

    if is_parent:
        parent_guardian = _create_parent(request)
        parent_guardian.patient.add(patient)
        parent_guardian.user = user
        parent_guardian.save()


def _create_django_user(request, django_user, registry, is_parent):
    if is_parent:
        user_group = _get_group("Parents")
    else:
        user_group = _get_group("Patients")

    django_user.groups = [user_group.id, ] if user_group else []

    django_user.first_name = request.POST['first_name']
    django_user.last_name = request.POST['surname']
    django_user.registry = [registry, ] if registry else []
    django_user.is_staff = True
    return django_user


def _create_patient_address(patient, request, address_type="POST"):
    from registry.patients.models import PatientAddress, AddressType
    address = PatientAddress.objects.create(
        patient=patient,
        address_type=AddressType.objects.get(description__icontains=address_type),
        address=request.POST["address"],
        suburb=request.POST["suburb"],
        state=request.POST["state"],
        postcode=request.POST["postcode"],
        country=request.POST["country"]
    )
    return address


def _create_parent(request):
    from registry.patients.models import ParentGuardian
    parent_guardian = ParentGuardian.objects.create(
        first_name=request.POST["parent_guardian_first_name"],
        last_name=request.POST["parent_guardian_last_name"],
        date_of_birth=request.POST["parent_guardian_date_of_birth"],
        gender=request.POST["parent_guardian_gender"],
        address=request.POST["parent_guardian_address"],
        suburb=request.POST["parent_guardian_suburb"],
        state=request.POST["parent_guardian_state"],
        postcode=request.POST["parent_guardian_postcode"],
        country=request.POST["parent_guardian_country"]
    )
    return parent_guardian


def _get_registry_object(registry_name):
    try:
        registry = Registry.objects.get(code__iexact=registry_name)
        return registry
    except Registry.DoesNotExist:
        return None


def _get_group(group_name):
    try:
        group, created = Group.objects.get_or_create(name=group_name)
        return group
    except Group.DoesNotExist:
        return None
