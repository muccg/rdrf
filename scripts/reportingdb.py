import django
django.setup()

from rdrf.models import Registry
from rdrf.reports import generator
from django.db import transaction
import logging
import sys

logger = logging.getLogger(__name__)

registry_code = sys.argv[1]
r = Registry.objects.get(code=registry_code)
g = generator.Generator(r)

with transaction.atomic():
    g.create_tables()

logger.info("FINISHED RUN!")
