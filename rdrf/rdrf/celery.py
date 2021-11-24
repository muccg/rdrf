import logging
from celery import Celery
from celery.signals import setup_logging
from django.conf import settings
from logging.config import dictConfig

logger = logging.getLogger(__name__)

logger.info("loading celery.py ...")
app = Celery('rdrf')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()


@setup_logging.connect
def config_loggers(*args, **kwags):
    dictConfig(settings.LOGGING)
