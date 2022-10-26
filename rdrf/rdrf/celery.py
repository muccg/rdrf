from celery import Celery
from celery.signals import setup_logging
from logging.config import dictConfig

app = Celery("rdrf")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()


@setup_logging.connect
def config_loggers(*args, **kwargs):
    dictConfig(settings.LOGGING)
