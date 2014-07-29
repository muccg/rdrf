#!/usr/bin/env python
import os
import os.path
import sys
import pwd

# Production centos django admin script
production_user = "apache"
webapp_root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
(uid, gid) = pwd.getpwnam('apache')[2:4]
os.setegid(gid)
os.seteuid(uid)
# setup the settings module for the WSGI app
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'defaultsettings.rdrf')
os.environ.setdefault('PROJECT_DIRECTORY', webapp_root)
os.environ.setdefault('WEBAPP_ROOT', webapp_root)
os.environ.setdefault('PYTHON_EGG_CACHE', '/tmp/.python-eggs')

if __name__ == "__main__":
    from django.core.management import execute_from_command_line
    if production_user:
        # prepare the settings module for the django app
        from ccg_django_utils.conf import setup_prod_env
        setup_prod_env("rdrf")
    else:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rdrf.settings")

    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
