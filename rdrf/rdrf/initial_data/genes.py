'''A large list of genes.'''

import os
from registry.genetic import models
from django.core import serializers


def load_data(**kwargs):
    filename = os.path.join(os.path.dirname(__file__), 'genes.json')
    with open(filename) as f:
        for gene in serializers.deserialize('json', f):
            gene.save()
