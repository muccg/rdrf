#!/usr/bin/env python
import os
import sys
import pwd

(uid, gid, gecos, homedir) = pwd.getpwnam('apache')[2:6]
os.setgid(gid)
os.setuid(uid)
os.environ["HOME"] = homedir

if __name__ == "__main__":

    webapp_name = os.path.basename(sys.argv[0])
    os.environ.setdefault('CCG_WEBAPPS_PREFIX', '/usr/local/webapps')
    webapp_root = os.path.join(os.environ['CCG_WEBAPPS_PREFIX'], webapp_name)

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
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'defaultsettings.rdrf')
    os.environ.setdefault('PROJECT_DIRECTORY', webapp_root)
    os.environ.setdefault('WEBAPP_ROOT', webapp_root)
    os.environ.setdefault('PYTHON_EGG_CACHE', '/tmp/.python-eggs')

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
