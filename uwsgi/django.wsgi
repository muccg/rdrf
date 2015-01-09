# Generic WSGI application
import os
import os.path
import django.core.handlers.wsgi

webapp_root = os.path.dirname(os.path.abspath(__file__))

def application(environ, start):

    # when served behind a reverse proxy and the path
    # is different between proxy and wsgi then HTTP_SCRIPT_NAME
    # must be set
    if "HTTP_SCRIPT_NAME" in environ:
        environ['SCRIPT_NAME']=environ['HTTP_SCRIPT_NAME']
        os.environ['SCRIPT_NAME']=environ['HTTP_SCRIPT_NAME']

    return django.core.handlers.wsgi.WSGIHandler()(environ,start)
