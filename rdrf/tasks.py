"""
Define events for use with the uWSGI cron-like interface (https://uwsgi-docs.readthedocs.io/en/latest/Cron.html)

Care must be taken with Django imports. We want application initialisation to be triggered by the web application
not by this file. Hence we are checking to see if the django app is ready before performing some imports.

"""
from django_uwsgi.decorators import timer
from django.apps import apps
import io
import logging

logger = logging.getLogger(__name__)

@timer(300)
def django_cron_heartbeat(num):
    """
    A heartbeat for django-cron (https://github.com/Tivix/django-cron)
    """

    if not apps.apps_ready:
        # Django is not initialised, the logger config in settings will not be active
        print("Deferring calling django-cron heartbeat until django app is ready")
        return

    # Do not perform this import until the django app is ready
    from django.core.management import call_command
    out_stream = io.StringIO("")
    logger.info("cron heartbeat: running crons ...")
    call_command('runcrons', stdout=out_stream)
    logger.info(out_stream.getvalue())
