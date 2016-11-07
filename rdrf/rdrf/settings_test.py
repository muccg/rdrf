from .settings import *

INSTALLED_APPS += [
    'aloe_django',
]

MIGRATION_MODULES = {"iprestrict": None}
IPRESTRICT_GEOIP_ENABLED = False
