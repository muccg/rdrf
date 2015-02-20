from django.contrib.auth.models import User as AuthUser
from django.contrib.auth.models import Group
from django.contrib.auth.models import AbstractUser, BaseUserManager

from django.db.models.signals import post_save
from django.db import models, transaction

from django.dispatch import receiver
from django.dispatch import receiver

from registration.signals import user_registered

from rdrf.models import Registry


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


@receiver(user_registered) 
def user_registered_callback(sender, user, request, **kwargs):
    user.first_name = request.POST['first_name']
    user.last_name = request.POST['surname']
    user.is_staff = True
    user.groups = [ _get_group("Patients"), ]
    
    registry_code = _get_registry_code(request.path)
    user.registry = [ _get_registry_object(registry_code), ]
    
    user.save()

def _get_registry_code(path):
    account = "accounts/"
    register ="/register"
    return (path.split(account))[1].split(register)[0]

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
