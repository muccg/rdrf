from django.conf import settings
from explorer import __version__

CSRF_NAME = getattr(settings, "CSRF_COOKIE_NAME", "csrf_token")

APP_VERSION = __version__
