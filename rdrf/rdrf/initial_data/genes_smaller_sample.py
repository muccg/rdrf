'''
A small sample of genes.

Avoids inserting the large list in genes.py. Can be used in development, testing etc.
'''

import os
from registry.genetic import models
from django.core import serializers


def load_data(**kwargs):
    filename = os.path.join(os.path.dirname(__file__), 'genes_smaller_sample.json')
    with open(filename) as f:
        for gene in serializers.deserialize('json', f):
            gene.save()
