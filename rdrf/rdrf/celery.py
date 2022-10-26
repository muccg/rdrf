from celery import Celery
from celery.signals import setup_logging
from logging.config import dictConfig
from django.conf import settings

app = Celery("rdrf")

app.config_from_object("django.conf:settings", namespace="CELERY")


@setup_logging.connect
def config_loggers(*args, **kwargs):
    dictConfig(settings.LOGGING)


app.autodiscover_tasks(["rdrf"])
