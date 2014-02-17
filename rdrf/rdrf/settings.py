# Django settings for rdrf project.
import os
from django.conf.global_settings import TEMPLATE_CONTEXT_PROCESSORS as TCP
# import message constants so we can use bootstrap style classes
from django.contrib.messages import constants as message_constants

WEBAPP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# General site config
DEBUG = True
DEV_SERVER = True
SITE_ID = 1
APPEND_SLASH = True
SSL_ENABLED = False

FORM_SECTION_DELIMITER = "____"

ROOT_URLCONF = 'rdrf.urls'

SECRET_KEY = 'qj#tl@9@7((%^)$i#iyw0gcfzf&#a*pobgb8yr#1%65+*6!@g$'

# Locale
TIME_ZONE = 'Australia/Perth'
LANGUAGE_CODE = 'en-us'
USE_I18N = True

VERSION = "0.4" # Used by exporter - todo mod version.py to update

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'rdrf',                      # Or path to database file if using sqlite3.
        'USER': 'rdrf',                      # Not used with sqlite3.
        'PASSWORD': 'rdrf',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Django Core stuff
TEMPLATE_LOADERS = [
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
]

TEMPLATE_DIRS = (
    os.path.join(WEBAPP_ROOT,'rdrf', 'templates'),
)

MESSAGE_TAGS = {message_constants.ERROR: 'alert alert-error',
                message_constants.SUCCESS:  'alert alert-success',
                message_constants.INFO:  'alert alert-info'}


MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'iprestrict.middleware.IPRestrictMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'ccg.middleware.ssl.SSLRedirect',
    'django.contrib.messages.middleware.MessageMiddleware',
)


INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'django.contrib.messages',
    'django_extensions',
    'suit',
    'south',
    'messages_ui',
    'userlog',
    'registry.groups',
    'registry.patients',
    'registry.genetic',
    'registry.common',
    'registry.configuration',

    'rdrf',
    'django_qbe',
    'django_qbe.savedqueries',
    'django.contrib.admin',
    'admin_views',
    'reversion',
    'iprestrict',

]



TEMPLATE_CONTEXT_PROCESSORS = TCP + (
    'django.core.context_processors.request',
)

# these determine which authentication method to use
# apps use modelbackend by default, but can be overridden here
# see: https://docs.djangoproject.com/en/dev/ref/settings/#authentication-backends
AUTHENTICATION_BACKENDS = [
 'django.contrib.auth.backends.ModelBackend'
]

# email
EMAIL_USE_TLS = False
EMAIL_HOST = '127.0.0.1'
EMAIL_PORT = 25

# default emails
ADMINS = [
    ('Tech Alerts', 'alerts@ccg.murdoch.edu.au')
]
MANAGERS = ADMINS


STATIC_ROOT = os.path.join(WEBAPP_ROOT, 'static')
STATIC_URL = '{0}/static/'.format(os.environ.get("SCRIPT_NAME", ""))

MEDIA_ROOT = os.path.join(WEBAPP_ROOT, 'media')
MEDIA_URL = '{0}/static/media/'.format(os.environ.get("SCRIPT_NAME", ""))

# for local development, this is set to the static serving directory. For deployment use Apache Alias
STATIC_SERVER_PATH = os.path.join(WEBAPP_ROOT, "static")

# a directory that will be writable by the webserver, for storing various files...
WRITABLE_DIRECTORY = "/tmp"
TEMPLATE_DEBUG = DEBUG

# session and cookies
SESSION_COOKIE_AGE = 60 * 60
SESSION_COOKIE_PATH = '{0}/'.format(os.environ.get("SCRIPT_NAME", ""))
SESSION_SAVE_EVERY_REQUEST = True
CSRF_COOKIE_NAME = "csrftoken_registry"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = False
SESSION_COOKIE_NAME = "rdrf"

# see https://docs.djangoproject.com/en/dev/ref/settings/#session-engine
# https://docs.djangoproject.com/en/1.3/ref/settings/#std:setting-SESSION_FILE_PATH
# in production we would suggest using memcached for your session engine
SESSION_ENGINE = 'django.contrib.sessions.backends.file'
SESSION_FILE_PATH = WRITABLE_DIRECTORY

# Testing settings
INSTALLED_APPS.extend(['django_nose'])
#TEST_RUNNER = 'rdrf.rdrf.tests.PatchedNoseTestSuiteRunner'
SOUTH_TESTS_MIGRATE = True
NOSE_ARGS = [
    '--with-coverage',
    '--cover-erase',
    '--cover-html',
    '--cover-branches',
    '--cover-package=rdrf',
]

# APPLICATION SPECIFIC SETTINGS
AUTH_PROFILE_MODULE = 'groups.User'
EMAIL_APP_NAME = "Registry "

# #
# # LOGGING
# #
LOG_DIRECTORY = os.path.join(WEBAPP_ROOT, "log")
try:
    if not os.path.exists(LOG_DIRECTORY):
        os.mkdir(LOG_DIRECTORY)
except:
    pass
os.path.exists(LOG_DIRECTORY), "No log directory, please create one: %s" % LOG_DIRECTORY

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'verbose': {
            'format': 'Registry [%(levelname)s:%(asctime)s:%(filename)s:%(lineno)s:%(funcName)s] %(message)s'
        },
        'db': {
            'format': 'Registry [%(duration)s:%(sql)s:%(params)s] %(message)s'
        },
        'simple': {
            'format': 'Registry %(levelname)s %(message)s'
        },
    },
    'filters': {
    },
    'handlers': {
        'null': {
            'level':'DEBUG',
            'class':'django.utils.log.NullHandler',
        },
        'console':{
            'level':'DEBUG',
            'class':'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'errorfile':{
            'level':'ERROR',
            'class':'logging.handlers.TimedRotatingFileHandler',
            'filename': os.path.join(LOG_DIRECTORY, 'error.log'),
            'when':'midnight',
            'formatter': 'verbose'
        },
        'registryfile':{
            'class':'logging.handlers.TimedRotatingFileHandler',
            'filename': os.path.join(LOG_DIRECTORY, 'registry.log'),
            'when':'midnight',
            'formatter': 'verbose'
        },
        'db_logfile':{
            'level':'DEBUG',
            'class':'logging.handlers.TimedRotatingFileHandler',
            'filename': os.path.join(LOG_DIRECTORY, 'registry_db.log'),
            'when':'midnight',
            'formatter': 'db'
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': [],
            'class': 'django.utils.log.AdminEmailHandler',
            'formatter':'verbose',
            'include_html':True
        }
    },
    'root': {
            'handlers':['console', 'errorfile', 'mail_admins'],
            'level':'ERROR',
    },
    'loggers': {
        'django': {
            'handlers':['null'],
            'propagate': False,
            'level':'INFO',
        },
        'registry_log': {
            'handlers': ['registryfile', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    }
}


################################################################################
## Customize settings for each registry below
################################################################################

INTERNAL_IPS = ('127.0.0.1', '172.16.2.1')

ALLOWED_HOSTS = [
    'localhost'
]

INSTALL_NAME = 'rdrf'

QBE_ACCESS_FOR = lambda user: user.is_superuser
LOGIN_URL = '{0}/login'.format(os.environ.get("SCRIPT_NAME", ""))

# Django Suit Config
SUIT_CONFIG = {
    'ADMIN_NAME': 'Rare Disease Registry Framework',

}
try:
    print "Attempting to import default settings as appsettings.rdrf"
    from appsettings.rdrf import *
    print "Successfully imported appsettings.rdrf"
except ImportError, e:
    print "Failed to import appsettings.rdrf"
