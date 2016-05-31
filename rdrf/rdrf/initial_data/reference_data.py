"""Reference data like address types, genetic techniques, etc.

Includes:
    - Address Types
    - Genetic Techniques
"""

from registry.patients.models import AddressType
from registry.genetic.models import Technique


def load_data(**kwargs):
    load_address_types()
    load_techniques()


def load_address_types():
    AddressType.objects.get_or_create(type="Home", description="Home Address")
    AddressType.objects.get_or_create(type="Postal", description="Postal Address")


def load_techniques():
    Technique.objects.get_or_create(name='MLPA')
    Technique.objects.get_or_create(name='Genomic DNA sequencing')
    Technique.objects.get_or_create(name='cDNA sequencing')
    Technique.objects.get_or_create(name='Array')
