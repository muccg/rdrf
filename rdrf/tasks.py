"""
Define events for use with the uWSGI cron-like interface (https://uwsgi-docs.readthedocs.io/en/latest/Cron.html)

Care must be taken with Django imports. We want application initialisation to be triggered by the web application
not by this file. Hence we are checking to see if the django app is ready before performing some imports.

"""
from django_uwsgi.decorators import timer
from django.apps import apps
import io
import os
import logging
import django

logger = logging.getLogger(__name__)


def webapp_initialised():
    # use a sentinel file
    return os.path.exists("/tmp/webapp_initialised")


@timer(300)
def django_cron_heartbeat(num):
    """
    A heartbeat for django-cron (https://github.com/Tivix/django-cron)
    """
    # fkrp #431 previous apps.apps_ready was working
    # but I suspect this was due to pre-forking being used.

    if not webapp_initialised():
        # Django is not initialised, the logger config in settings will not be active
        print("Deferring calling django-cron heartbeat until django app is ready")
        return

    # safe to load
    try:
        django.setup()
    except RuntimeError as r:
        if str(r) == "populate() isn't reentrant":
            return
    
    # Do not perform this import until the django app is ready
    from django.core.management import call_command
    out_stream = io.StringIO("")
    logger.info("cron heartbeat: running crons ...")
    call_command('runcrons', stdout=out_stream)
    logger.info(out_stream.getvalue())
