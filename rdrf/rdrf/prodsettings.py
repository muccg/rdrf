from settings import *
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-#
# Default debug mode is off, turn on for trouble-shooting
#DEBUG = False
# Default SSL on and forced, turn off if necessary
#SSL_ENABLED = True
#SSL_FORCE = True
#SESSION_COOKIE_SECURE = True
#CSRF_COOKIE_SECURE = True
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-#
# FROM original puppetdata appsettings erb file for rdrf-prod.py.erb
TEMPLATE_DIRS = (
    os.path.join(CCG_INSTALL_ROOT, 'rdrf', 'templates')
)

TEMPLATE_LOADERS = [
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
]

ALLOWED_HOSTS = env.getlist("allowed_hosts", ['.ccgapps.com.au'])

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    #'iprestrict.middleware.IPRestrictMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'ccg.middleware.ssl.SSLRedirect',
    'django.contrib.messages.middleware.MessageMiddleware',
)
