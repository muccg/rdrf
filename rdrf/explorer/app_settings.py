from django.conf import settings
from explorer import __version__

# These are no longer used to construct client - rdrf.mongo_client.construct_mongo_client is instead
VIEWER_MONGO_HOST = getattr(settings, "MONGOSERVER", 'localhost')
VIEWER_MONGO_PORT = getattr(settings, "MONGOPORT", 27017)

CSRF_NAME = getattr(settings, "CSRF_COOKIE_NAME", "csrf_token")

APP_VERSION = __version__
