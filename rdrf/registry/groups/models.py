from django.db import models, transaction
from django.contrib.auth.models import User as AuthUser
from django.contrib.auth.models import Group
from rdrf.models import Registry
from django.db.models.signals import post_save

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.dispatch import receiver

from registration.signals import user_registered

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

 
def user_registered_callback(sender, user, request, **kwargs):
    user.first_name = request.POST['first_name']
    user.last_name = request.POST['surname']
    user.is_staff = True
    user.groups = [_get_group("Patients"),]
    user.save()

def _get_group(group_name):
    group = Group.objects.get(name__contains = group_name)
    return group

user_registered.connect(user_registered_callback)
