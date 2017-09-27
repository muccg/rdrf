VERSION = "2.3.1"
__version__ = VERSION

# Ensures db router system check is registered
from . import db


default_app_config = 'rdrf.apps.RDRFConfig'
