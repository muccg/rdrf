# Generic WSGI application
import os
import django.core.handlers.wsgi

def application(environ, start):

    # HTTP_SCRIPT_NAME is potentially set by a reverse proxy
    # copy to os.environ so the application can access from settings.py
    if "HTTP_SCRIPT_NAME" in environ:
        os.environ['HTTP_SCRIPT_NAME'] = environ['HTTP_SCRIPT_NAME']

    return django.core.handlers.wsgi.WSGIHandler()(environ,start)
