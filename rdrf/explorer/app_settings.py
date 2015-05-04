from django.conf import settings
from explorer import __version__

VIEWER_MONGO_HOST = getattr(settings, "MONGOSERVER", 'localhost')
VIEWER_MONGO_PORT = getattr(settings, "MONGOPOSRT", 27017)

CSRF_NAME = getattr(settings, "CSRF_COOKIE_NAME", "csrf_token")

APP_VERSION = __version__
