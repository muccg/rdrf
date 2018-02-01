'''
Initial users with different roles.

Includes users:
    - admin
    - curator
    - clinical
    - genetic
'''
from django.contrib.auth.models import Group
from registry.groups import models


deps = ['groups']


def load_data(**kwargs):
    create_user('admin', groups=['Working Group Curators'], is_superuser=True)
    create_user('curator', groups=['Working Group Curators'])
    create_user('clinical', groups=['Clinical Staff'])
    create_user('genetic', groups=['Genetic Staff'])


def create_user(username, password=None, groups=[], **kwargs):
    if password is None:
        password = username
    defaults = dict(
        email='%s@example.com' % username,
        first_name=username,
        last_name=username,
        is_active=True,
        is_staff=True,
    )
    defaults.update(kwargs)

    user, created = models.CustomUser.objects.get_or_create(
        username=username, defaults=defaults)
    if created:
        user.set_password(password)
        user.groups.add(*Group.objects.filter(name__in=groups))
        user.save()
