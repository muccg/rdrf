import re

from django.core import validators
from django.contrib.auth.models import AbstractBaseUser, UserManager, PermissionsMixin
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.db import models
from django.dispatch import receiver

from registration.signals import user_registered
from rdrf.models import Registry
from registry.groups import GROUPS as RDRF_GROUPS

import logging

logger = logging.getLogger(__name__)


class WorkingGroup(models.Model):
    name = models.CharField(max_length=100)
    registry = models.ForeignKey(Registry, null=True)

    class Meta:
        ordering = ["registry__code"]

    def __str__(self):
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
    username = models.CharField(
        _('username'),
        max_length=254,
        unique=True,
        help_text=_('Required. 254 characters or fewer. Letters, numbers and @/./+/-/_ characters'),
        validators=[
            validators.RegexValidator(
                re.compile('^[\w.@+-]+$'),
                _('Enter a valid username.'),
                _('invalid'))])
    first_name = models.CharField(_('first name'), max_length=30)
    last_name = models.CharField(_('last name'), max_length=30)
    email = models.EmailField(_('email address'), max_length=254)
    is_staff = models.BooleanField(_('staff status'), default=False,
                                   help_text=_('Designates whether the user can log into this admin site.'))
    is_active = models.BooleanField(_('active'), default=False, help_text=_(
        'Designates whether this user should be treated as active. Unselect this instead of deleting accounts.'))
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)

    working_groups = models.ManyToManyField(WorkingGroup, blank=True, related_name='working_groups')
    title = models.CharField(max_length=50, null=True, blank=True, verbose_name="position")
    registry = models.ManyToManyField(Registry, blank=True, related_name='registry')
    password_change_date = models.DateTimeField(auto_now_add=True, null=True)

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
    def can_archive(self):
        """
        can user soft delete patients
        """
        value = False

        if self.is_superuser:
            value =  True
            logger.debug("user is super user so can archive")
        else:
            logger.debug("user is NOT superuser")
            value = self.has_perm("patients.delete_patient")
            logger.debug("%s delete patient perm = %s" % (self, value))
        
        return value

    @property
    def notices(self):
        from rdrf.models import Notification
        return Notification.objects.filter(
            to_username=self.username,
            seen=False).order_by("-created")

    def in_registry(self, registry_model):
        return self.registry.filter(pk=registry_model.pk).exists()

    def in_group(self, name):
        return self.groups.filter(name__icontains=name).exists()

    @property
    def is_patient(self):
        return self.in_group(RDRF_GROUPS.PATIENT)

    @property
    def is_parent(self):
        return self.in_group(RDRF_GROUPS.PARENT)

    @property
    def is_clinician(self):
        return self.in_group(RDRF_GROUPS.CLINICAL)

    @property
    def is_genetic_staff(self):
        return self.in_group(RDRF_GROUPS.GENETIC_STAFF)

    @property
    def is_genetic_curator(self):
        return self.in_group(RDRF_GROUPS.GENETIC_CURATOR)

    @property
    def is_working_group_staff(self):
        return self.in_group(RDRF_GROUPS.WORKING_GROUP_STAFF)

    @property
    def is_curator(self):
        return self.in_group(RDRF_GROUPS.WORKING_GROUP_CURATOR)

    def get_groups(self):
        return self.groups.all()

    def get_working_groups(self):
        return self.working_groups.all()

    def get_registries(self):
        return self.registry.all()

    def get_registries_or_all(self):
        if not self.is_superuser:
            return self.get_registries()
        else:
            return Registry.objects.all().order_by("name")

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
    def menu_links(self):
        from rdrf.quick_links import QuickLinks
        qlinks = QuickLinks(self.get_registries_or_all())
        if self.is_superuser:
            links = qlinks.menu_links([RDRF_GROUPS.SUPER_USER])
        else:
            links = qlinks.menu_links([group.name for group in self.groups.all()])

        return links

    @property
    def settings_links(self):
        links = []

        if self.is_superuser:
            from rdrf.quick_links import QuickLinks
            qlinks = QuickLinks(self.get_registries_or_all())
            links = qlinks.settings_links()

        return links

    @property
    def admin_page_links(self):
        links = []

        if self.is_superuser:
            from rdrf.quick_links import QuickLinks
            qlinks = QuickLinks(self.get_registries_or_all())
            links = qlinks.admin_page_links()

        return links


@receiver(user_registered)
def user_registered_callback(sender, user, request, **kwargs):

    reg_code = request.POST['registry_code']

    patient_reg = None
    if reg_code == "fkrp":
        from fkrp.patient_registration import FkrpRegistration
        patient_reg = FkrpRegistration(user, request)
    elif reg_code == "ang":
        from angelman.patient_registration import AngelmanRegistration
        patient_reg = AngelmanRegistration(user, request)
    elif reg_code == "mtm":
        from mtm.patient_registration import MtmRegistration
        patient_reg = MtmRegistration(user, request)

    patient_reg.process()
