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

fi = os.environ.get('DJANGO_FIXTURES')

deps = []

# "dev" for runserver
if fi == "dev":
    deps = [
        'reference_data',
        'users',
        'sample_laboratories',
        'genes_smaller_sample',
        'iprestrict_permissive',
    ]

# "none" for bahavioural and "test" for unit tests
if fi == "none" or fi == "test":
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
