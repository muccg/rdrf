# Generic WSGI application
import os
from django.core.wsgi import get_wsgi_application

def application(environ, start):

    # copy any vars into os.environ
    for key in environ:
        os.environ[key] = str(environ[key])

    return get_wsgi_application()(environ,start)
