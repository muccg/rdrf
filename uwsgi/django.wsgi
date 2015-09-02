# Generic WSGI application
import os
from django.core.wsgi import get_wsgi_application

def application(environ, start):

    # copy any vars into os.environ
    for key in environ:
        os.environ[key] = str(environ[key])

    #2/9/2015 TODO: remove hardcoded HTTP_X_FORWARDED_HOST when nginx container fixed
    environ["HTTP_X_FORWARDED_HOST"] = "localhost:8443"

    return get_wsgi_application()(environ,start)
