from .celery import app as celery_app
# Ensures db router system check is registered

VERSION = "6.2.1"
__version__ = VERSION


default_app_config = 'rdrf.apps.RDRFConfig'

__all__ = ('celery_app',)
