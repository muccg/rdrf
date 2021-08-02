from django.db import models
import logging
from rdrf.models.definition.models import Registry


logger = logging.getLogger(__name__)


class DataRequest(models.Model):
    umrn = models.CharField(max_length=80)
