import os
from setuptools import setup

package_data = {}
start_dir = os.getcwd()
requirements=[
    "Django==1.10.2",
    "pymongo==2.9.3",
    "pyyaml==3.12",
    "django-extensions>=0.7.1",
    "django-templatetag-sugar==1.0",
    "pyparsing==2.1.9",
    "python-memcached==1.58",
    "django-messages-ui==0.2.7",
    "django-templatetag-handlebars==1.3.1",
    "django-ajax-selects",
    "setuptools_scm==1.10.1",
    "django-positions ",
    "pycountry==1.20",
    "django-countries",
    "uwsgi==2.0.13.1",
    "pyinotify==0.9.6",
    "django-registration-redux==1.3",
    "psycopg2==2.6.1",
    "djangorestframework==3.4.7",
    "openpyxl==2.3.5",
    "SQLAlchemy==1.0.15",
    "django-anymail==0.4.2",
    "ccg-django-utils==0.4.2",
    "django-useraudit==1.3.1",
    "django-iprestrict==1.0.1",
    "python-dateutil==2.5.3",
    "polib==1.0.7",
    "django-storages==1.4.1",
    "pyodbc==3.0.7",
    "django-nose==1.4.4",
    "geoip2==2.4.0",
    "six==1.10.0",
]


def add_file_for_package(package, subdir, f):
    full_path = os.path.join(subdir, f)
    # print "%s: %s" % (package, full_path)
    return full_path

packages = ['rdrf',
            'registry',
            'registry.common',
            'registry.patients',
            'registry.groups',
            'registry.genetic',
            'explorer',
            ]

for package in ['rdrf', 'registry.common', 'registry.genetic',
                'registry.groups', 'registry.patients', 'registry.humangenome', 'explorer']:
    package_data[package] = []
    if "." in package:
        base_dir, package_dir = package.split(".")
        os.chdir(os.path.join(start_dir, base_dir, package_dir))
    else:
        base_dir = package
        os.chdir(os.path.join(start_dir, base_dir))

    for data_dir in (
            'templates',
            'static',
            'migrations',
            'fixtures',
            'features',
            'hooks',
            'templatetags',
            'management'):
        package_data[package].extend([add_file_for_package(package, subdir, f) for (
            subdir, dirs, files) in os.walk(data_dir) for f in files])

    os.chdir(start_dir)


setup(name='django-rdrf',
      version="1.6.10",
      packages=packages,
      description='RDRF',
      long_description='Rare Disease Registry Framework',
      author='Centre for Comparative Genomics',
      author_email='rdrf@ccg.murdoch.edu.au',
      package_data=package_data,
      zip_safe=False,
      install_requires=requirements
      )
