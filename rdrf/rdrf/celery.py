from celery import Celery
import logging

logger = logging.getLogger(__name__)

logger.info("loading celery.py")
app = Celery('rdrf')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()
