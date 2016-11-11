from .settings import *

INSTALLED_APPS += [
    'aloe_django',
]

IPRESTRICT_GEOIP_ENABLED = False

# https://code.djangoproject.com/ticket/16713
del DATABASES["clinical"]
