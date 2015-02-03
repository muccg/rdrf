# Django settings for rdrf project.
import os
from ccg_django_utils.conf import EnvConfig  # A wrapper around environment which has been populated from /etc/rdrf/rdrf.conf in production. Also does type conversion of values
from django.conf.global_settings import TEMPLATE_CONTEXT_PROCESSORS as TCP
# import message constants so we can use bootstrap style classes
from django.contrib.messages import constants as message_constants

env = EnvConfig()

SCRIPT_NAME = env.get("script_name", os.environ.get("HTTP_SCRIPT_NAME", "")) 
FORCE_SCRIPT_NAME = env.get("force_script_name", "") or SCRIPT_NAME or None

WEBAPP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# General site config
PRODUCTION = env.get("production", False)
SSL_ENABLED = PRODUCTION
SSL_FORCE = PRODUCTION
DEBUG = env.get("debug", not PRODUCTION)
SITE_ID = env.get("site_id", 1)
APPEND_SLASH = env.get("append_slash", True)

FORM_SECTION_DELIMITER = "____"

ROOT_URLCONF = 'rdrf.urls'

SECRET_KEY = env.get("secret_key", "changeme")
# Locale
TIME_ZONE = env.get("time_zone", 'Australia/Perth')
LANGUAGE_CODE = env.get("language_code", 'en-us')
USE_I18N = env.get("use_i18n", True)

DATABASES = {
    'default': {
        'ENGINE': env.get_db_engine("dbtype", "pgsql"),         # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': env.get("dbname", "rdrf"),                      # Or path to database file if using sqlite3.
        'USER': env.get("dbuser", "rdrf"),                      # Not used with sqlite3.
        'PASSWORD': env.get("dbpass", "rdrf"),                  # Not used with sqlite3.
        'HOST': env.get("dbserver", ""),                        # Set to empty string for localhost. Not used with sqlite3.
        'PORT': env.get("dbport", ""),                          # Set to empty string for default. Not used with sqlite3.
    }
}

MONGOSERVER = env.get("mongoserver", "localhost")
MONGOPORT = env.get("mongoport", 27017)

# Django Core stuff
TEMPLATE_LOADERS = [
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
]

TEMPLATE_DIRS = (
    os.path.join(WEBAPP_ROOT, 'rdrf', 'templates'),
)

MESSAGE_TAGS = {
    message_constants.ERROR: 'alert alert-danger',
    message_constants.SUCCESS: 'alert alert-success',
    message_constants.INFO: 'alert alert-info'
}

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    #'iprestrict.middleware.IPRestrictMiddleware',
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
    'rdrf',
    'registry.groups',
    'registry.patients',
    'registry.common',
    'registry.genetic',
    'django.contrib.admin',
    'iprestrict',
    'ajax_select',
    'notification',
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
EMAIL_USE_TLS = env.get("email_use_tls", False)
EMAIL_HOST = env.get("email_host", '127.0.0.1')
EMAIL_PORT = env.get("email_port", 25)
EMAIL_HOST_USER = env.get("email_host_user", "")
EMAIL_HOST_PASSWORD = env.get("email_host_password", "")
EMAIL_APP_NAME = env.get("email_app_name", "RDRF {0}".format(SCRIPT_NAME))
EMAIL_SUBJECT_PREFIX = env.get("email_subject_prefix", "DEV {0}".format(SCRIPT_NAME))
SERVER_EMAIL = env.get("server_email", "noreply@ccg_rdrf")

# default emailsn
ADMINS = [
    ('alerts', env.get("alert_email", "root@localhost"))
]
MANAGERS = ADMINS


STATIC_ROOT = env.get('static_root', os.path.join(WEBAPP_ROOT, 'static'))
STATIC_URL = '{0}/static/'.format(SCRIPT_NAME)

MEDIA_ROOT = env.get('media_root', os.path.join(WEBAPP_ROOT, 'static', 'media'))
MEDIA_URL = '{0}/static/media/'.format(SCRIPT_NAME)

# TODO AH I can't see how this setting does anything
# for local development, this is set to the static serving directory. For deployment use Apache Alias
STATIC_SERVER_PATH = STATIC_ROOT

# a directory that will be writable by the webserver, for storing various files...
WRITABLE_DIRECTORY = env.get("writable_directory", "/tmp")
TEMPLATE_DEBUG = DEBUG

# session and cookies
SESSION_COOKIE_AGE = env.get("session_cookie_age", 60 * 60)
SESSION_COOKIE_PATH = '{0}/'.format(SCRIPT_NAME)
SESSION_SAVE_EVERY_REQUEST = env.get("session_save_every_request", True)
SESSION_COOKIE_HTTPONLY = env.get("session_cookie_httponly", True)
SESSION_COOKIE_SECURE = env.get("session_cookie_secure", PRODUCTION)
SESSION_COOKIE_NAME = env.get("session_cookie_name", "rdrf_{0}".format(SCRIPT_NAME.replace("/", "")))
SESSION_COOKIE_DOMAIN = env.get("session_cookie_domain", "") or None
CSRF_COOKIE_NAME = env.get("csrf_cookie_name", "csrf_{0}".format(SESSION_COOKIE_NAME))
CSRF_COOKIE_DOMAIN = env.get("csrf_cookie_domain", "") or SESSION_COOKIE_DOMAIN
CSRF_COOKIE_PATH = env.get("csrf_cookie_path", SESSION_COOKIE_PATH)
CSRF_COOKIE_SECURE = env.get("csrf_cookie_secure", PRODUCTION)

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
ALLOWED_HOSTS = env.getlist("allowed_hosts", ["*"])

# This honours the X-Forwarded-Host header set by our nginx frontend when
# constructing redirect URLS.
# see: https://docs.djangoproject.com/en/1.4/ref/settings/#use-x-forwarded-host
USE_X_FORWARDED_HOST = env.get("use_x_forwarded_host", True)

if env.get("memcache", ""):
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
            'LOCATION': env.getlist("memcache"),
            'KEY_PREFIX': env.get("key_prefix", "rdrf")
        }
    }

    SESSION_ENGINE = "django.contrib.sessions.backends.cache"
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
            'LOCATION': 'rdrf_cache',
            'TIMEOUT': 3600,
            'MAX_ENTRIES': 600
        }
    }

    SESSION_ENGINE = 'django.contrib.sessions.backends.file'
    SESSION_FILE_PATH = WRITABLE_DIRECTORY

# #
# # LOGGING
# #
LOG_DIRECTORY = env.get('log_directory', os.path.join(WEBAPP_ROOT, "log"))
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
            'level': 'DEBUG',
            'class': 'django.utils.log.NullHandler',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'errorfile': {
            'level': 'ERROR',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': os.path.join(LOG_DIRECTORY, 'error.log'),
            'when': 'midnight',
            'formatter': 'verbose'
        },
        'registryfile': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': os.path.join(LOG_DIRECTORY, 'registry.log'),
            'when': 'midnight',
            'formatter': 'verbose'
        },
        'db_logfile': {
            'level': 'DEBUG',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': os.path.join(LOG_DIRECTORY, 'registry_db.log'),
            'when': 'midnight',
            'formatter': 'db'
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': [],
            'class': 'django.utils.log.AdminEmailHandler',
            'formatter': 'verbose',
            'include_html': True
        }
    },
    'root': {
        'handlers': ['console', 'errorfile', 'mail_admins'],
        'level': 'ERROR',
    },
    'loggers': {
        'django': {
            'handlers': ['null'],
            'propagate': False,
            'level': 'INFO',
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

AUTH_USER_MODEL = 'groups.CustomUser'

INTERNAL_IPS = ('127.0.0.1', '172.16.2.1')

INSTALL_NAME = env.get("install_name", 'rdrf')

# Django Suit Config
SUIT_CONFIG = {
    'ADMIN_NAME': 'Rare Disease Registry Framework',
    'MENU_OPEN_FIRST_CHILD': False,
    'MENU_EXCLUDE': ('sites', 'rdrf.questionnaireresponse'),

    'MENU': (
        'auth',
        'genetic',
        'groups',
        'iprestrict',
        'patients',
        {'app': 'rdrf', 'label': 'Registry'},
        {'app': 'rdrf', 'label': 'Questionnaires', 'models': [
                {'label': 'Responses', 'url': 'admin:rdrf_questionnaireresponse_changelist'}
        ]}
    )
}

'''
One can add custom menu items to the left hand manu in Django Suit
'''
CUSTOM_MENU_ITEMS = [
    {'name': 'Import Registry Definition', 'url': '{0}/import'.format(SCRIPT_NAME), 'superuser': True},
]

AJAX_LOOKUP_CHANNELS = {
    'gene': {'model': 'genetic.Gene', 'search_field': 'symbol'},
}
