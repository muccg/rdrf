# Generic WSGI application for use with CCG Django projects
# Installed by RPM package

import os
import os.path
import sys

# snippet to enable the virtualenv
activate_this=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bin', 'activate_this.py')
if os.path.exists(activate_this):
    exec(compile(open(activate_this).read(), activate_this, 'exec'), dict(__file__=activate_this))
del activate_this

webapp_root = os.path.dirname(os.path.abspath(__file__))

# prepare the settings module for the WSGI app
from ccg_django_utils.conf import setup_prod_env
setup_prod_env("rdrf")

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
