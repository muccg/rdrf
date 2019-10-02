import sys
import logging
from django.db import transaction
from rdrf.reports import generator
from rdrf.models.definition.models import Registry
import django
django.setup()


logger = logging.getLogger(__name__)

registry_code = sys.argv[1]
r = Registry.objects.get(code=registry_code)
g = generator.Generator(r)

with transaction.atomic():
    g.create_tables()

logger.info("end of reportingdb.py")
