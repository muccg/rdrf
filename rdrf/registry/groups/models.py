from django.db import models, transaction
from django.contrib.auth.models import User as AuthUser
from rdrf.models import Registry

class WorkingGroup(models.Model):
    name = models.CharField(max_length=40)

    class Meta:
        ordering = ["name"]

    def __unicode__(self):
        return self.name


class User(models.Model):
    user = models.OneToOneField(AuthUser, primary_key=True)
    title = models.CharField(max_length=50, verbose_name="position")
    working_groups = models.ManyToManyField(WorkingGroup, null=True, related_name = 'working_group')
    registry = models.ManyToManyField(Registry, null=False, blank=False, related_name='registry')

    class Meta:
        ordering = ["user__username"]

    def __unicode__(self):
        return str(self.user)

    @transaction.commit_on_success
    def delete(self, *args, **kwargs):
        user = self.user
        super(User, self).delete(*args, **kwargs)

        # Kill the django.contrib.auth record as well.
        user.delete()


# Signal handlers.

from django.db.models.signals import post_save

def user_post_save_handler(sender, instance, **kwargs):
    profile, new = User.objects.get_or_create(user=instance)

post_save.connect(user_post_save_handler, sender=AuthUser)
