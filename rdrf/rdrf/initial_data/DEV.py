'''
Collection of datasets to be used by developers.

Includes:
    - reference data
    - users and groups
    - laboratories, small sample of genes
    - sample registry
    - permissive iprestrict rules
'''
from registry.groups import models


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
