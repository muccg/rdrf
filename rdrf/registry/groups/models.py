from django.db import models, transaction
from django.contrib.auth.models import User as AuthUser
from rdrf.models import Registry

from django.contrib.auth.models import AbstractUser, BaseUserManager

class WorkingGroup(models.Model):
    name = models.CharField(max_length=40)

    class Meta:
        ordering = ["name"]

    def __unicode__(self):
        return self.name


class CustomUser(AbstractUser):
    working_groups = models.ManyToManyField(WorkingGroup, null=True, related_name = 'working_groups')
    title = models.CharField(max_length=50, null=True, verbose_name="position")
    registry = models.ManyToManyField(Registry, null=False, blank=False, related_name='registry')
