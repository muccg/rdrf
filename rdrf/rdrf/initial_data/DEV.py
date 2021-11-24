'''
Collection of datasets to be used by developers.

Includes:
    - reference data
    - users and groups
    - laboratories, small sample of genes
    - sample registry, only if a sample registry to be created
    - permissive iprestrict rules
'''
import os
from registry.groups import models

fixtures = os.environ.get('DJANGO_FIXTURES')


def is_dev():
    return fixtures == "dev"


def is_test():
    return fixtures in ["none", "test"]


deps = []

if is_dev():
    deps = [
        'reference_data',
        'users',
        'iprestrict_permissive',
    ]

if is_test():
    deps = [
        'reference_data',
        'users',
        'sample_laboratories',
        'genes_smaller_sample',
        'sample_registry',
        'iprestrict_permissive',
    ]


def load_data(**kwargs):
    pass
