#!/usr/bin/env python
import os
import os.path
import sys
import pwd

# Production centos django admin script

webapp_root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

(uid, gid) = pwd.getpwnam('apache')[2:4]
os.setegid(gid)
os.seteuid(uid)

# Allow appsettings to be imported
sys.path.insert(0, "/etc/ccgapps")

# setup the settings module for the WSGI app
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'defaultsettings.rdrf')
os.environ.setdefault('PROJECT_DIRECTORY', webapp_root)
os.environ.setdefault('WEBAPP_ROOT', webapp_root)
os.environ.setdefault('PYTHON_EGG_CACHE', '/tmp/.python-eggs')

if __name__ == "__main__":
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
