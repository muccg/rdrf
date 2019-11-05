# Django settings for rdrf project.
from django_auth_ldap.config import LDAPSearch
from django_auth_ldap.config import PosixGroupType
from django_auth_ldap.config import GroupOfNamesType
from django_auth_ldap.config import ActiveDirectoryGroupType
import ldap
import os
# A wrapper around environment which has been populated from
# /etc/rdrf/rdrf.conf in production. Also does type conversion of values
from ccg_django_utils.conf import EnvConfig
# import message constants so we can use bootstrap style classes
from django.contrib.messages import constants as message_constants
from rdrf.system_role import SystemRoles

env = EnvConfig()
# testing travis 2

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

# If iprestrict by location is enabled then the MaxMind database needs
# to be available.
IPRESTRICT_GEOIP_ENABLED = env.get("iprestrict_geoip_enabled", False)
GEOIP_PATH = env.get("geoip_path", os.path.join(WEBAPP_ROOT, "geoip"))

DEBUG = env.get("debug", not PRODUCTION)
SITE_ID = env.get("site_id", 1)
APPEND_SLASH = env.get("append_slash", True)

FORM_SECTION_DELIMITER = "____"

IMPORT_MODE = False

ROOT_URLCONF = 'rdrf.urls'

SESSION_EXPIRE_AT_BROWSER_CLOSE = True

SECRET_KEY = env.get("secret_key", "changeme")
# Locale
TIME_ZONE = env.get("time_zone", 'Australia/Perth')
LANGUAGE_CODE = env.get("language_code", 'en')
USE_I18N = env.get("use_i18n", True)

# This must be a superset of LANGUAGES
ALL_LANGUAGES = (("en", "English"),
                 ("ar", "Arabic"),
                 ("pl", "Polish"),
                 ("es", "Spanish"),
                 ("de", "German"),
                 ("fr", "French"),
                 ("it", "Italian"))


# EnvConfig can't handle structure of tuple of tuples so we pass in a flat association list
# E.g. ["en","English","ar","Arabic"]
# This must be a subset of ALL_LANGUAGES
LANGUAGES_ASSOC_LIST = env.getlist("languages", ["en", "English"])
LANGUAGES = tuple(zip(LANGUAGES_ASSOC_LIST[0::2], LANGUAGES_ASSOC_LIST[1::2]))


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

# Clinical database (defaults to main db if not specified).
DATABASES["clinical"] = {
    "ENGINE": env.get_db_engine("clinical_dbtype", "pgsql"),
    "NAME": env.get("clinical_dbname", DATABASES["default"]["NAME"]),
    "USER": env.get("clinical_dbuser", DATABASES["default"]["USER"]),
    "PASSWORD": env.get("clinical_dbpass", DATABASES["default"]["PASSWORD"]),
    "HOST": env.get("clinical_dbserver", DATABASES["default"]["HOST"]),
    "PORT": env.get("clinical_dbport", DATABASES["default"]["PORT"]),
}

DATABASES["reporting"] = {
    "ENGINE": env.get_db_engine("reporting_dbtype", "pgsql"),
    "NAME": env.get("reporting_dbname", DATABASES["default"]["NAME"]),
    "USER": env.get("reporting_dbuser", DATABASES["default"]["USER"]),
    "PASSWORD": env.get("reporting_dbpass", DATABASES["default"]["PASSWORD"]),
    "HOST": env.get("reporting_dbserver", DATABASES["default"]["HOST"]),
    "PORT": env.get("reporting_dbport", DATABASES["default"]["PORT"]),
}

DATABASE_ROUTERS = ["rdrf.db.db.RegistryRouter"]


TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(WEBAPP_ROOT, 'rdrf', 'templates')],
        "APP_DIRS": False,
        "OPTIONS": {
            "context_processors": [
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.debug",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.request",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
                "rdrf.context_processors.context_processors.production",
                "rdrf.context_processors.context_processors.common_settings",
                "rdrf.context_processors.context_processors.cic_system_role",

            ],
            "debug": DEBUG,
            "loaders": [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
                'rdrf.template_loaders.translation.Loader'
            ]
        },
    },
]

MESSAGE_TAGS = {
    message_constants.ERROR: 'alert alert-danger',
    message_constants.SUCCESS: 'alert alert-success',
    message_constants.INFO: 'alert alert-info'
}

# Always store messages in the session, as the default storage sometimes
# shows up messages addressed to other users.
MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

MIDDLEWARE = (
    'useraudit.middleware.RequestToThreadLocalMiddleware',
    'django.middleware.common.CommonMiddleware',
    'iprestrict.middleware.IPRestrictMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_otp.middleware.OTPMiddleware',
    'registry.common.middleware.EnforceTwoFactorAuthMiddleware',
    'session_security.middleware.SessionSecurityMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django_user_agents.middleware.UserAgentMiddleware',
)


INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'django.contrib.messages',
    'django_extensions',
    'django.contrib.admin',
    'messages_ui',
    'ajax_select',
    'explorer',
    'useraudit',
    'templatetag_handlebars',
    'iprestrict',
    'rest_framework',
    'anymail',
    'rdrf',
    'registry.groups',
    'registry.patients',
    'registry.common',
    'registry.genetic',
    'registration',
    'reversion',
    'storages',
    'django_otp',
    'django_otp.plugins.otp_static',
    'django_otp.plugins.otp_totp',
    'two_factor',
    'django_user_agents',
    'formtools',
    'session_security'
]


# LDAP
LDAP_ENABLED = env.get("ldap_enabled", False)

# Default values used by our development ldap container.
# Comment out the ldap/phpldapadmin containers in docker-compose.yml to test locally.
DEV_LDAP_URL = "ldap://ldap"
DEV_LDAP_DC = "dc=example,dc=com"
DEV_LDAP_DN = "cn=admin,dc=example,dc=com"
DEV_LDAP_GROUP = "ou=groups,dc=example,dc=com"
DEV_LDAP_IS_ACTIVE_GROUP = "cn=active,ou=groups,dc=example,dc=com"
DEV_LDAP_IS_SUPERUSER_GROUP = "cn=superuser,ou=groups,dc=example,dc=com"
DEV_LDAP_PASSWORD = "admin"
DEV_LDAP_FIRST_NAME_ATTR = "sn"
DEV_LDAP_LAST_NAME_ATTR = "sn"
DEV_LDAP_MAIL_ATTR = "mail"
DEV_LDAP_GROUP_TYPE_ATTR = "cn"
DEV_LDAP_REGISTRY_CODE = "ICHOMCRC"
DEV_LDAP_AUTH_GROUP = "Clinical Staff"
DEV_LDAP_WORKING_GROUP = "RPH"
DEV_LDAP_GROUP_PERMS = False
DEV_LDAP_CACHE_GROUPS = False
DEV_LDAP_CACHE_TIMEOUT = 1  # Default to 1 hour.

# these enviroment variables are prefixed RDRF_ to not conflict with the variables expected by LDAP auth middleware.
RDRF_AUTH_LDAP_BIND_DC = env.get("rdrf_auth_ldap_bind_dc", DEV_LDAP_DC)
RDRF_AUTH_LDAP_BIND_GROUP = env.get("rdrf_auth_ldap_bind_group", DEV_LDAP_GROUP)
RDRF_AUTH_LDAP_FIRST_NAME_ATTR = env.get("rdrf_auth_ldap_first_name_attr", DEV_LDAP_FIRST_NAME_ATTR)
RDRF_AUTH_LDAP_LAST_NAME_ATTR = env.get("rdrf_auth_ldap_last_name_attr", DEV_LDAP_LAST_NAME_ATTR)
RDRF_AUTH_LDAP_MAIL_ATTR = env.get("rdrf_auth_ldap_mail_attr", DEV_LDAP_MAIL_ATTR)
RDRF_AUTH_LDAP_IS_ACTIVE_GROUP = env.get("rdrf_auth_ldap_is_active_group", DEV_LDAP_IS_ACTIVE_GROUP)
RDRF_AUTH_LDAP_IS_SUPERUSER_GROUP = env.get("rdrf_auth_ldap_is_superuser_group", DEV_LDAP_IS_SUPERUSER_GROUP)
RDRF_AUTH_LDAP_GROUP_TYPE_ATTR = env.get("rdrf_auth_ldap_group_type_attr", DEV_LDAP_GROUP_TYPE_ATTR)
RDRF_AUTH_LDAP_REGISTRY_CODE = env.get("rdrf_auth_ldap_registry_code", DEV_LDAP_REGISTRY_CODE)
RDRF_AUTH_LDAP_AUTH_GROUP = env.get("rdrf_auth_ldap_auth_group", DEV_LDAP_AUTH_GROUP)
RDRF_AUTH_LDAP_WORKING_GROUP = env.get("rdrf_auth_ldap_working_group", DEV_LDAP_WORKING_GROUP)
RDRF_AUTH_LDAP_ALLOW_SUPERUSER = env.get("rdrf_auth_ldap_allow_superuser", False)
RDRF_AUTH_LDAP_FORCE_ISACTIVE = env.get("rdrf_auth_ldap_force_isactive", True)
RDRF_AUTH_LDAP_REQUIRE_2FA = env.get("rdrf_auth_ldap_require_2fa", False)
RDRF_AUTH_LDAP_GROUP_SEARCH_TYPE = env.get("rdrf_auth_ldap_group_search_type", "posix")
RDRF_AUTH_LDAP_GROUP_SEARCH_FIELD = env.get("rdrf_auth_ldap_group_search_field", "objectClass")
RDRF_AUTH_LDAP_GROUP_SEARCH_FIELD_VALUE = env.get("rdrf_auth_ldap_group_search_field_value", "posixGroup")
RDRF_AUTH_LDAP_USER_SEARCH_ATTR = env.get("rdrf_auth_ldap_user_search_attr", "uid")

# LDAP auth middleware env variables.

# LDAP connection variables.
AUTH_LDAP_SERVER_URI = env.get("auth_ldap_server_uri", DEV_LDAP_URL)
AUTH_LDAP_BIND_DN = env.get("auth_ldap_bind_dn", DEV_LDAP_DN)
AUTH_LDAP_BIND_PASSWORD = env.get("auth_ldap_bind_password", DEV_LDAP_PASSWORD)

# Matching LDAP user fields to RDRF user fields.
AUTH_LDAP_USER_ATTR_MAP = {"first_name": RDRF_AUTH_LDAP_FIRST_NAME_ATTR,
                           "last_name": RDRF_AUTH_LDAP_LAST_NAME_ATTR,
                           "email": RDRF_AUTH_LDAP_MAIL_ATTR}

# LDAP User Search settings.
AUTH_LDAP_USER_SEARCH = LDAPSearch(RDRF_AUTH_LDAP_BIND_DC, ldap.SCOPE_SUBTREE,
                                   f"({RDRF_AUTH_LDAP_USER_SEARCH_ATTR}=%(user)s)")

# Matching LDAP user group to user settings (superuser / active)
AUTH_LDAP_USER_FLAGS_BY_GROUP = {}
if RDRF_AUTH_LDAP_ALLOW_SUPERUSER:
    AUTH_LDAP_USER_FLAGS_BY_GROUP['is_superuser'] = RDRF_AUTH_LDAP_IS_SUPERUSER_GROUP
if not RDRF_AUTH_LDAP_FORCE_ISACTIVE:
    AUTH_LDAP_USER_FLAGS_BY_GROUP['is_active'] = RDRF_AUTH_LDAP_IS_ACTIVE_GROUP

# LDAP Group Search settings.
AUTH_LDAP_GROUP_SEARCH = LDAPSearch(RDRF_AUTH_LDAP_BIND_GROUP, ldap.SCOPE_SUBTREE,
                                    f"({RDRF_AUTH_LDAP_GROUP_SEARCH_FIELD}={RDRF_AUTH_LDAP_GROUP_SEARCH_FIELD_VALUE})")
if RDRF_AUTH_LDAP_GROUP_SEARCH_TYPE == "posix":
    AUTH_LDAP_GROUP_TYPE = PosixGroupType(name_attr=RDRF_AUTH_LDAP_GROUP_TYPE_ATTR)
elif RDRF_AUTH_LDAP_GROUP_SEARCH_TYPE == "groupofnames":
    AUTH_LDAP_GROUP_TYPE = GroupOfNamesType(name_attr=RDRF_AUTH_LDAP_GROUP_TYPE_ATTR)
elif RDRF_AUTH_LDAP_GROUP_SEARCH_TYPE == "activedirectory":
    AUTH_LDAP_GROUP_TYPE = ActiveDirectoryGroupType(name_attr=RDRF_AUTH_LDAP_GROUP_TYPE_ATTR)
AUTH_LDAP_FIND_GROUP_PERMS = env.get("auth_ldap_find_group_perms", DEV_LDAP_GROUP_PERMS)
AUTH_LDAP_CACHE_GROUPS = env.get("auth_ldap_cache_groups", DEV_LDAP_CACHE_GROUPS)
AUTH_LDAP_GROUP_CACHE_TIMEOUT = env.get("auth_ldap_group_cache_timeout", DEV_LDAP_CACHE_TIMEOUT)

# Security: set required LDAP group (user must be in this LDAP group to login in RDRF)
AUTH_LDAP_REQUIRE_GROUP = env.get("auth_ldap_require_group", "")

# these determine which authentication method to use
# apps use modelbackend by default, but can be overridden here
# see: https://docs.djangoproject.com/en/dev/ref/settings/#authentication-backends

AUTHENTICATION_BACKENDS = [
    'useraudit.password_expiry.AccountExpiryBackend',
    'django.contrib.auth.backends.ModelBackend',
    'useraudit.backend.AuthFailedLoggerBackend',
]
if LDAP_ENABLED:
    AUTHENTICATION_BACKENDS.insert(0, 'rdrf.auth.ldap_backend.RDRFLDAPBackend')


# email
EMAIL_USE_TLS = env.get("email_use_tls", False)
EMAIL_HOST = env.get("email_host", 'smtp')
EMAIL_PORT = env.get("email_port", 25)
EMAIL_HOST_USER = env.get("email_host_user", "webmaster@localhost")
EMAIL_HOST_PASSWORD = env.get("email_host_password", "")
EMAIL_APP_NAME = env.get("email_app_name", "RDRF {0}".format(SCRIPT_NAME))
EMAIL_SUBJECT_PREFIX = env.get("email_subject_prefix", "DEV {0}".format(SCRIPT_NAME))

# Email Notifications
# NB. This initialises the email notification form
DEFAULT_FROM_EMAIL = env.get('default_from_email', 'No Reply <no-reply@mg.ccgapps.com.au>')
SERVER_EMAIL = env.get('server_email', DEFAULT_FROM_EMAIL)
EMAIL_BACKEND = 'anymail.backends.mailgun.EmailBackend'

ANYMAIL = {
    'MAILGUN_API_KEY': env.get('DJANGO_MAILGUN_API_KEY', ''),
}

# default emailsn
ADMINS = [
    ('alerts', env.get("alert_email", "root@localhost"))
]
MANAGERS = ADMINS


STATIC_ROOT = env.get('static_root', os.path.join(WEBAPP_ROOT, 'static'))
STATIC_URL = '{0}/static/'.format(SCRIPT_NAME)

# TODO AH I can't see how this setting does anything
# for local development, this is set to the static serving directory. For
# deployment use Apache Alias
STATIC_SERVER_PATH = STATIC_ROOT

# a directory that will be writable by the webserver, for storing various files...
WRITABLE_DIRECTORY = env.get("writable_directory", "/tmp")

# valid values django.core.files.storage.FileSystemStorage and
# storages.backends.database.DatabaseStorage
DEFAULT_FILE_STORAGE = env.get("storage_backend", "django.core.files.storage.FileSystemStorage")

# settings used when FileSystemStorage is enabled
MEDIA_ROOT = env.get('media_root', os.path.join(WEBAPP_ROOT, 'uploads'))
MEDIA_URL = '{0}/uploads/'.format(SCRIPT_NAME)

# setting used when DatabaseStorage is enabled
DB_FILES = {
    "db_table": "rdrf_filestorage",
    "fname_column": "name",
    "blob_column": "data",
    "size_column": "size",
    "base_url": None,
}
DATABASE_ODBC_DRIVER = "{PostgreSQL}"  # depends on odbcinst.ini
DATABASE_NAME = DATABASES["default"]["NAME"]
DATABASE_USER = DATABASES["default"]["USER"]
DATABASE_PASSWORD = DATABASES["default"]["PASSWORD"]
DATABASE_HOST = DATABASES["default"]["HOST"]

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
CSRF_COOKIE_AGE = env.get("csrf_cookie_age", 31449600)
CSRF_FAILURE_VIEW = env.get("csrf_failure_view", "django.views.csrf.csrf_failure")
CSRF_HEADER_NAME = env.get("csrf_header_name", 'HTTP_X_CSRFTOKEN')
CSRF_TRUSTED_ORIGINS = env.getlist("csrf_trusted_origins", ['localhost'])


# The maximum size in bytes that a request body may be before a
# SuspiciousOperation (RequestDataTooBig) is raised.
DATA_UPLOAD_MAX_MEMORY_SIZE = env.get("data_upload_max_memory_size", 2621440) or None
# The maximum number of parameters that may be received via GET or
# POST before a SuspiciousOperation (TooManyFields) is raised.
DATA_UPLOAD_MAX_NUMBER_FIELDS = env.get("data_upload_max_number_fields", 30000) or None

# django-useraudit
# The setting `LOGIN_FAILURE_LIMIT` allows to enable a number of allowed login attempts.
# If the settings is not set or set to 0, the feature is disabled.
LOGIN_FAILURE_LIMIT = env.get("login_failure_limit", 3)

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


# Default LOG patient_model fieldname
LOG_PATIENT_FIELDNAME = env.get('log_patient_fieldname', 'id')

# Log handlers
DEFAULT_LOG_HANDLER = ['console', 'file']
MAILADMIN_LOG_HANDLER = ['mail_admins']
COMMAND_LOG_HANDLER = ['shell', 'admin_command_file']
IMPORT_LOG_HANDLER = ['console_simple']

# Add the syslog handler when syslog is enabled.
DOCKER_HOST_IP = "172.21.0.1"
DEFAULT_RSYSLOG_PORT = 514
SYSLOG_ENABLED = env.get("syslog_enabled", False)
SYSLOG_ADDRESS = env.get("syslog_address", DOCKER_HOST_IP)
SYSLOG_PORT = int(env.get("syslog_port", DEFAULT_RSYSLOG_PORT))
if SYSLOG_ENABLED:
    DEFAULT_LOG_HANDLER.append('syslog')
    MAILADMIN_LOG_HANDLER.append('syslog')
    COMMAND_LOG_HANDLER.append('syslog')
    IMPORT_LOG_HANDLER.append('syslog')

# UserAgent lookup cache location - used by django_user_agents
USER_AGENTS_CACHE = 'default'

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
            'class': 'logging.NullHandler',
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
        'file': {
            'level': 'INFO',
            'class': 'ccg_django_utils.loghandlers.ParentPathFileHandler',
            'filename': os.path.join(LOG_DIRECTORY, 'registry.log'),
            'when': 'midnight',
            'formatter': 'verbose'
        },
        'admin_command_file': {
            'level': 'INFO',
            'class': 'ccg_django_utils.loghandlers.ParentPathFileHandler',
            'filename': os.path.join(LOG_DIRECTORY, 'admin_command.log'),
            'when': 'midnight',
            'formatter': 'verbose'
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': True
        },
        'syslog': {
            'level': 'INFO',
            'class': 'logging.handlers.SysLogHandler',
            'formatter': 'verbose',
            # uncomment next line if rsyslog works with unix socket only (UDP reception disabled)
            'address': (SYSLOG_ADDRESS, SYSLOG_PORT)
        }
    },
    'loggers': {
        '': {
            'handlers': DEFAULT_LOG_HANDLER,
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': True
        },
        'django.request': {
            'handlers': MAILADMIN_LOG_HANDLER,
            'level': 'ERROR',
            'propagate': True,
        },
        'django.security': {
            'handlers': MAILADMIN_LOG_HANDLER,
            'level': 'ERROR',
            'propagate': True,
        },
        'django.db.backends': {
            'handlers': MAILADMIN_LOG_HANDLER,
            'level': 'CRITICAL',
            'propagate': True,
        },
        'rdrf.management.commands': {
            'handlers': COMMAND_LOG_HANDLER,
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'rdrf.export_import': {
            'handlers': IMPORT_LOG_HANDLER,
            'formatter': 'simplest',
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    }
}

# Design Mode:
# True means forms. sections, cdes can be edited in Django admin
# False ( the default) means registry definition cannot be edited on site
DESIGN_MODE = env.get('design_mode', False)


################################################################################
# Customize settings for each registry below
################################################################################

AUTH_USER_MODEL = 'groups.CustomUser'
AUTH_USER_MODEL_PASSWORD_CHANGE_DATE_ATTR = "password_change_date"

# How long a user's password is good for. None or 0 means no expiration.
PASSWORD_EXPIRY_DAYS = env.get("password_expiry_days", 180)
# How long before expiry will the frontend start bothering the user
PASSWORD_EXPIRY_WARNING_DAYS = env.get("password_expiry_warning_days", 30)
# Disable the user's account if they haven't logged in for this time
ACCOUNT_EXPIRY_DAYS = env.get("account_expiry_days", 100)

# Allow users to unlock their accounts by requesting a reset link in email and then visiting it
ACCOUNT_SELF_UNLOCK_ENABLED = env.get("account_self_unlock_enabled", True)

INTERNAL_IPS = ('127.0.0.1', '172.16.2.1')

INSTALL_NAME = env.get("install_name", 'rdrf')

AJAX_LOOKUP_CHANNELS = {
    'gene': {'model': 'genetic.Gene', 'search_field': 'symbol'},
}

ACCOUNT_ACTIVATION_DAYS = 2

LOGIN_URL = '{0}/account/login'.format(SCRIPT_NAME)
LOGIN_REDIRECT_URL = '{0}/'.format(SCRIPT_NAME)


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.DjangoModelPermissions',
    ),
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.NamespaceVersioning',
    'DEFAULT_VERSION': 'v1',
}

SYSTEM_ROLE = SystemRoles.get_role(env)
PROJECT_TITLE = env.get("project_title", "Rare Disease Registry Framework")
PROJECT_TITLE_LINK = "admin:index" if SYSTEM_ROLE == SystemRoles.CIC_PROMS else "patientslisting"

# project logo and link
PROJECT_LOGO = env.get("project_logo", "")
PROJECT_LOGO_LINK = env.get("project_logo_link", "")


LOCALE_PATHS = env.getlist("locale_paths", [os.path.join(WEBAPP_ROOT, "translations/locale")])

AUTH_PASSWORD_VALIDATORS = [{
    'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    'OPTIONS': {
            'min_length': env.get("password_min_length", 8),
    }
},
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
},
    {
        'NAME': 'rdrf.auth.password_validation.HasUppercaseLetterValidator',
},
    {
        'NAME': 'rdrf.auth.password_validation.HasLowercaseLetterValidator',
},
    {
        'NAME': 'rdrf.auth.password_validation.HasNumberValidator',
},
    {
        'NAME': 'rdrf.auth.password_validation.HasSpecialCharacterValidator',
},
]

# setup for PROMS
PROMS_SECRET_TOKEN = env.get("proms_secret_token", "foobar")  # todo set this us in env etc
PROMS_USERNAME = env.get("proms_username", "promsuser")
PROMS_LOGO = env.get("proms_logo", "")


SESSION_SECURITY_ENABLE = env.get("session_security_enable", False)
if SESSION_SECURITY_ENABLE:
    SESSION_SECURITY_WARN_AFTER = env.get("session_security_warn_after", 480)
    SESSION_SECURITY_EXPIRE_AFTER = env.get("session_security_expire_after", 600)

# Enable user password change
ENABLE_PWD_CHANGE = env.get("enable_pwd_change", True)
