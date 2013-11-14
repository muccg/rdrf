# Generic WSGI application for use with CCG Django projects
# Installed by RPM package

import os, sys

webapp_root = os.path.dirname(os.path.abspath(__file__))

# Path hackery to make sure all the project's paths appear
# before the system paths in sys.path. addsitedir always
# appends unfortunately.
import site
oldpath = sys.path[1:]
sys.path = sys.path[:1]
site.addsitedir(webapp_root)
site.addsitedir(os.path.join(webapp_root, "lib"))
site.addsitedir("/etc/ccgapps")
site.addsitedir("/usr/local/etc/ccgapps")
sys.path.extend(oldpath)

# setup the settings module for the WSGI app
os.environ['DJANGO_SETTINGS_MODULE'] = 'defaultsettings.dmd'
os.environ['PROJECT_DIRECTORY'] = webapp_root
os.environ['WEBAPP_ROOT'] = webapp_root
os.environ['PYTHON_EGG_CACHE'] = '/tmp/.python-eggs'

import django.core.handlers.wsgi

# This is the WSGI application booter
def application(environ, start):
    if "HTTP_SCRIPT_NAME" in environ:
        environ['SCRIPT_NAME']=environ['HTTP_SCRIPT_NAME']
        os.environ['SCRIPT_NAME']=environ['HTTP_SCRIPT_NAME']
    else:
        os.environ['SCRIPT_NAME']=environ['SCRIPT_NAME']
    if 'DJANGODEV' in environ:
       os.environ['DJANGODEV']=environ['DJANGODEV']
    return django.core.handlers.wsgi.WSGIHandler()(environ,start)
