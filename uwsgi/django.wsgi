# Generic WSGI application
import os
import django.core.handlers.wsgi

def application(environ, start):

    # copy any vars into os.environ
    for key in environ:
        os.environ[key] = environ[key]

    return django.core.handlers.wsgi.WSGIHandler()(environ,start)
