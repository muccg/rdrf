'''
Initial groups for different roles.

Includes groups:
    - Working Group Curators
    - Clinical Staff
    - Genetic Staff
'''
from django.contrib.auth.models import Group

from registry.groups.group_permissions import add_permissions_to_group


def create_group(name):
    group, _ = Group.objects.get_or_create(name=name)
    add_permissions_to_group(group, name)


def load_data(**kwargs):
    create_group('Working Group Curators')
    create_group('Clinical Staff')
    create_group('Genetic Staff')
