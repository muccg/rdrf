# Generic WSGI application
import os
import django.core.handlers.wsgi

import django
django.setup()

def application(environ, start):

    # copy any vars into os.environ
    for key in environ:
        os.environ[key] = str(environ[key])

    return django.core.handlers.wsgi.WSGIHandler()(environ,start)
