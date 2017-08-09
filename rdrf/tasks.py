"""
Define events for use with the uWSGI cron-like interface (https://uwsgi-docs.readthedocs.io/en/latest/Cron.html)

"""
from django_uwsgi.decorators import timer
from django.core.management import call_command
from django.conf import settings
import io
import logging


logger = logging.getLogger(__name__)


import django
django.setup()


if settings.DEBUG:
    @timer(60)
    def debug_timer(num):
        logger.debug("")


@timer(300)
def django_cron_heartbeat(num):
    """
    A heartbeat for django-cron (https://github.com/Tivix/django-cron)
    """
    out_stream = io.StringIO("")
    call_command('runcrons', stdout=out_stream)
    logger.info(out_stream.getvalue())
