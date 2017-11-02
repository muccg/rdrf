import django
django.setup()

from rdrf.models import Registry
from rdrf.reports import schema
from django.db import transaction
import logging


logger = logging.getLogger(__name__)



dmd = Registry.objects.get(code="DMD")

g = schema.Generator(dmd)


with transaction.atomic():
    try:
        g.create_tables()
    except Exception as ex:
        logger.debug("Error creating tables: %s" % ex)

        
