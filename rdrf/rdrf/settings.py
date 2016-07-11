# Django settings for rdrf project.
import os
import ssl

# A wrapper around environment which has been populated from
# /etc/rdrf/rdrf.conf in production. Also does type conversion of values
from ccg_django_utils.conf import EnvConfig
from django.conf.global_settings import TEMPLATE_CONTEXT_PROCESSORS as TCP
# import message constants so we can use bootstrap style classes
from django.contrib.messages import constants as message_constants

env = EnvConfig()

SCRIPT_NAME = env.get("script_name", os.environ.get("HTTP_SCRIPT_NAME", ""))
FORCE_SCRIPT_NAME = env.get("force_script_name", "") or SCRIPT_NAME or None

WEBAPP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# General site config
PRODUCTION = env.get("production", False)

# https://docs.djangoproject.com/en/1.8/ref/middleware/#django.middleware.security.SecurityMiddleware
SECURE_SSL_REDIRECT = env.get("secure_ssl_redirect", PRODUCTION)
SECURE_SSL_HOST = env.get("secure_ssl_host", False)
SECURE_CONTENT_TYPE_NOSNIFF = env.get("secure_content_type_nosniff", PRODUCTION)
SECURE_BROWSER_XSS_FILTER = env.get("secure_browser_xss_filter", PRODUCTION)
SECURE_REDIRECT_EXEMPT = env.getlist("secure_redirect_exempt", [])
X_FRAME_OPTIONS = env.get("x_frame_options", 'DENY')

# iprestrict config https://github.com/muccg/django-iprestrict
IPRESRICT_TRUSTED_PROXIES = env.getlist("iprestrict_trusted_proxies", [])
IPRESTRICT_RELOAD_RULES = env.get("iprestrict_reload_rules", True)
IPRESTRICT_IGNORE_PROXY_HEADER = env.get("iprestrict_ignore_proxy_header", False)

DEBUG = env.get("debug", not PRODUCTION)
SITE_ID = env.get("site_id", 1)
APPEND_SLASH = env.get("append_slash", True)

FORM_SECTION_DELIMITER = "____"

ROOT_URLCONF = 'rdrf.urls'

SESSION_EXPIRE_AT_BROWSER_CLOSE = True

SECRET_KEY = env.get("secret_key", "changeme")
# Locale
TIME_ZONE = env.get("time_zone", 'Australia/Perth')
LANGUAGE_CODE = env.get("language_code", 'en')
USE_I18N = env.get("use_i18n", True)

LANGUAGES = (
    ('ar', 'Arabic'),
    ('de', 'German'),
    ('en', 'English'),
    ('no', 'Norwegian'),
)

DATABASES = {
    'default': {
        # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'ENGINE': env.get_db_engine("dbtype", "pgsql"),
        # Or path to database file if using sqlite3.
        'NAME': env.get("dbname", "rdrf"),
        'USER': env.get("dbuser", "rdrf"),                      # Not used with sqlite3.
        'PASSWORD': env.get("dbpass", "rdrf"),                  # Not used with sqlite3.
        # Set to empty string for localhost. Not used with sqlite3.
        'HOST': env.get("dbserver", ""),
        # Set to empty string for default. Not used with sqlite3.
        'PORT': env.get("dbport", ""),
    }
}
# 'legacydb': {
#     'ENGINE': env.get_db_engine("dbtype", "pgsql"),
#     'NAME': "legacyrdrf",
#     'USER': "legacyrdrf",
#     'PASSWORD': "legacyrdrf",
#     'HOST': "legacydb",
#     'PORT': "5432",


# Reporing Database ( defaults to main db if not specified
DATABASES["reporting"] = {}

DATABASES["reporting"]['ENGINE']   = env.get_db_engine("reporting_dbtype", "pgsql")
DATABASES["reporting"]['NAME']     = env.get("reporting_dbname",   DATABASES["default"]["NAME"])
DATABASES["reporting"]['USER']     = env.get("reporting_dbuser",   DATABASES["default"]["USER"])
DATABASES["reporting"]['PASSWORD'] = env.get("reporting_dbpass",   DATABASES["default"]["PASSWORD"])
DATABASES["reporting"]['HOST']     = env.get("reporting_dbserver", DATABASES["default"]["HOST"])
DATABASES["reporting"]['PORT']     = env.get("reporting_dbport",   DATABASES["default"]["PORT"])

# Mongo Settings - see http://api.mongodb.org/python/2.8.1/api/pymongo/mongo_client.html for usage
# These settings ( and only )  are consumed by rdrf.mongo_client

MONGOSERVER = env.get("mongoserver", "localhost")
MONGOPORT = env.get("mongoport", 27017)
MONGO_DB_PREFIX = env.get("mongo_db_prefix", "")

MONGO_CLIENT_MAX_POOL_SIZE = env.get("mongo_max_pool_size", 100)
MONGO_CLIENT_TZ_AWARE = env.get("mongo_client_tz_aware", False)
MONGO_CLIENT_CONNECT = env.get("mongo_client_connect", True)

MONGO_CLIENT_SOCKET_TIMEOUT_MS = env.get("mongo_client_socket_timeout_ms", "") or None
MONGO_CLIENT_CONNECT_TIMEOUT_MS = env.get("mongo_client_connect_timeout_ms", 20000)
MONGO_CLIENT_WAIT_QUEUE_TIMEOUT_MS = env.get("mongo_client_wait_queue_timeout_ms", "") or None
MONGO_CLIENT_WAIT_QUEUE_MULTIPLE = env.get("mongo_client_wait_queue_multiple", "") or None
MONGO_CLIENT_SOCKET_KEEP_ALIVE = env.get("mongo_client_socket_keep_alive", False)

MONGO_CLIENT_SSL = env.get("mongo_client_ssl", False)
MONGO_CLIENT_SSL_KEYFILE = env.get("mongo_client_ssl_keyfile", "") or None
MONGO_CLIENT_SSL_CERTFILE = env.get("mongo_client_ssl_certfile", "") or None
MONGO_CLIENT_SSL_CERT_REQS = env.get("mongo_client_ssl_cert_reqs", "") or ssl.CERT_NONE
MONGO_CLIENT_SSL_CA_CERTS = env.get("mongo_client_ssl_ca_certs", "") or None


# Django Core stuff
TEMPLATE_LOADERS = [
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    'django.template.loaders.eggs.Loader',
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
    'useraudit.middleware.RequestToThreadLocalMiddleware',
    'django.middleware.common.CommonMiddleware',
    'iprestrict.middleware.IPRestrictMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
)


INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'django.contrib.messages',
    'django_extensions',
    'messages_ui',
    'rdrf',
    'registry.groups',
    'registry.patients',
    'registry.common',
    'registry.genetic',
    'django.contrib.admin',
    'ajax_select',
    'registration',
    'explorer',
    'useraudit',
    'templatetag_handlebars',
    'iprestrict',
    'rest_framework',
]


TEMPLATE_CONTEXT_PROCESSORS = TCP + (
    'django.core.context_processors.i18n',
    'django.core.context_processors.request',
)

# these determine which authentication method to use
# apps use modelbackend by default, but can be overridden here
# see: https://docs.djangoproject.com/en/dev/ref/settings/#authentication-backends
AUTHENTICATION_BACKENDS = [
    'useraudit.password_expiry.AccountExpiryBackend',
    'django.contrib.auth.backends.ModelBackend',
    'useraudit.backend.AuthFailedLoggerBackend'
]

# email
EMAIL_USE_TLS = env.get("email_use_tls", False)
EMAIL_HOST = env.get("email_host", 'smtp')
EMAIL_PORT = env.get("email_port", 25)
EMAIL_HOST_USER = env.get("email_host_user", "webmaster@localhost")
EMAIL_HOST_PASSWORD = env.get("email_host_password", "")
EMAIL_APP_NAME = env.get("email_app_name", "RDRF {0}".format(SCRIPT_NAME))
EMAIL_SUBJECT_PREFIX = env.get("email_subject_prefix", "DEV {0}".format(SCRIPT_NAME))
SERVER_EMAIL = env.get("server_email", "noreply@ccg_rdrf")

# Django Notifications
DEFAULT_FROM_EMAIL = env.get("default_from_email", "No Reply <no-reply@mg.ccgapps.com.au>")
# Mail Gun
EMAIL_BACKEND = 'django_mailgun.MailgunBackend'
MAILGUN_ACCESS_KEY = env.get('DJANGO_MAILGUN_API_KEY', "")
MAILGUN_SERVER_NAME = env.get('DJANGO_MAILGUN_SERVER_NAME', "")
SERVER_EMAIL = env.get('DJANGO_SERVER_EMAIL', DEFAULT_FROM_EMAIL)

# list of features  '*' means all , '' means none and ['x','y'] means site
# supports features x and y
FEATURES = env.get("features", "*")


# default emailsn
ADMINS = [
    ('alerts', env.get("alert_email", "root@localhost"))
]
MANAGERS = ADMINS


STATIC_ROOT = env.get('static_root', os.path.join(WEBAPP_ROOT, 'static'))
STATIC_URL = '{0}/static/'.format(SCRIPT_NAME)

MEDIA_ROOT = env.get('media_root', os.path.join(WEBAPP_ROOT, 'uploads'))
MEDIA_URL = '{0}/uploads/'.format(SCRIPT_NAME)

# TODO AH I can't see how this setting does anything
# for local development, this is set to the static serving directory. For
# deployment use Apache Alias
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
SESSION_COOKIE_NAME = env.get(
    "session_cookie_name", "rdrf_{0}".format(SCRIPT_NAME.replace("/", "")))
SESSION_COOKIE_DOMAIN = env.get("session_cookie_domain", "") or None
CSRF_COOKIE_NAME = env.get("csrf_cookie_name", "csrf_{0}".format(SESSION_COOKIE_NAME))
CSRF_COOKIE_DOMAIN = env.get("csrf_cookie_domain", "") or SESSION_COOKIE_DOMAIN
CSRF_COOKIE_PATH = env.get("csrf_cookie_path", SESSION_COOKIE_PATH)
CSRF_COOKIE_SECURE = env.get("csrf_cookie_secure", PRODUCTION)
CSRF_COOKIE_HTTPONLY = env.get("csrf_cookie_httponly", True)

# Testing settings
INSTALLED_APPS.extend(['django_nose'])

TEST_RUNNER = 'xmlrunner.extra.djangotestrunner.XMLTestRunner'

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
ALLOWED_HOSTS = env.getlist("allowed_hosts", ["localhost"])

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

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[%(levelname)s:%(asctime)s:%(filename)s:%(lineno)s:%(funcName)s] %(message)s'
        },
        'db': {
            'format': '[%(duration)s:%(sql)s:%(params)s] %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
        'simplest': {
            'format': '%(message)s'
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'null': {
            'level': 'DEBUG',
            'class': 'django.utils.log.NullHandler',
        },
        'console': {
            'level': 'DEBUG',
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'console_simple': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simplest'
        },
        'shell': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'console_simple': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simplest'
        },
        'file': {
            'level': 'INFO',
            'class': 'ccg_django_utils.loghandlers.ParentPathFileHandler',
            'filename': os.path.join(LOG_DIRECTORY, 'registry.log'),
            'when': 'midnight',
            'formatter': 'verbose'
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': True
        },
        'null': {
            'class': 'django.utils.log.NullHandler',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': True
        },
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        'django.security': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        'django.db.backends': {
            'handlers': ['mail_admins'],
            'level': 'CRITICAL',
            'propagate': True,
        },
        'rdrf.rdrf.management.commands': {
            'handlers': ['shell'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'rdrf.export_import': {
            'handlers': ['console_simple'],
            'formatter': 'simplest',
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    }
}


################################################################################
# Customize settings for each registry below
################################################################################

AUTH_USER_MODEL = 'groups.CustomUser'
AUTH_USER_MODEL_PASSWORD_CHANGE_DATE_ATTR = "password_change_date"

# How long a user's password is good for. None or 0 means no expiration.
PASSWORD_EXPIRY_DAYS = 180
# How long before expiry will the frontend start bothering the user
PASSWORD_EXPIRY_WARNING_DAYS = 30
# Disable the user's account if they haven't logged in for this time
ACCOUNT_EXPIRY_DAYS = 100


INTERNAL_IPS = ('127.0.0.1', '172.16.2.1')

INSTALL_NAME = env.get("install_name", 'rdrf')

AJAX_LOOKUP_CHANNELS = {
    'gene': {'model': 'genetic.Gene', 'search_field': 'symbol'},
}

ACCOUNT_ACTIVATION_DAYS = 2

LOGIN_URL = '{0}/login'.format(SCRIPT_NAME)
LOGIN_REDIRECT_URL = '{0}/'.format(SCRIPT_NAME)


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.DjangoModelPermissions',
    ),
    'DEFAULT_VERSIONING_CLASS' : 'rest_framework.versioning.NamespaceVersioning',
    'DEFAULT_VERSION': 'v1',
}

EMAIL_NOTE_OTHER_CLINICIAN = "other-clinician"
EMAIL_NOTE_NEW_PATIENT = "new-patient"

EMAIL_NOTIFICATIONS = (
    (EMAIL_NOTE_OTHER_CLINICIAN, "Other Clinician"),
    (EMAIL_NOTE_NEW_PATIENT, "New Patient Registered")
)
