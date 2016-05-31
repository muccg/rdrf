'''
Initial groups for different roles.

Includes groups:
    - Working Group Curators
    - Clinical Staff
    - Genetic Staff
'''
from django.contrib.auth.models import Group


def load_data(**kwargs):
    Group.objects.get_or_create(name='Working Group Curators')
    Group.objects.get_or_create(name='Clinical Staff')
    Group.objects.get_or_create(name='Genetic Staff')
