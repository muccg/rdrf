from .celery import app as celery_app
# Ensures db router system check is registered

VERSION = "6.1.19"
__version__ = VERSION


default_app_config = 'rdrf.apps.RDRFConfig'

__all__ = ('celery_app',)
