import os
from setuptools import setup, find_packages

package_data = {}
start_dir = os.getcwd()
requirements = [
    "ccg-django-utils==0.4.2",
    "Django==1.10.8",
    "django-ajax-selects==1.5.2",
    "django-anymail==0.11.1",
    "django-countries",
    "django-extensions>=0.7.1",
    "django-iprestrict==1.1.1",
    "django-messages-ui==0.2.7",
    "django-nose==1.4.4",
    "django-positions==0.5.4",
    "django-registration-redux==1.4",
    "djangorestframework==3.5.3",
    "django-storages==1.4.1",
    "django-templatetag-handlebars==1.3.1",
    "django-templatetag-sugar==1.0",
    "django-useraudit==1.6.0",
    "django-uwsgi==0.2.1",
    "geoip2==2.4.0",
    "jsonschema==2.5.1",
    "openpyxl==2.3.5",
    "polib==1.0.8",
    "psycopg2==2.7.3",
    "pycountry==1.20",
    "pyinotify==0.9.6",
    "pyodbc==3.0.7",
    "pyparsing==2.1.10",
    "python-dateutil==2.5.3",
    "python-memcached==1.58",
    "pyyaml==3.12",
    "setuptools>=36.0.0,<=37.0.0",
    "setuptools_scm==1.10.1",
    "six==1.10.0",
    "SQLAlchemy==1.0.16",
    "uwsgi==2.0.13.1",
    "django_cron==0.5.0",

    # django-two-factor-auth dependencies
    "django-formtools==2.0",
    "django-otp==0.4.1.1",
    "django-phonenumber-field==1.3.0",
    "django-two-factor-auth==1.6.2",
    "phonenumberslite==8.8.1",
    "qrcode==4.0.4",
]


def add_file_for_package(package, subdir, f):
    full_path = os.path.join(subdir, f)
    # print "%s: %s" % (package, full_path)
    return full_path


packages = ['rdrf',
            'rdrf.account_handling',
            'rdrf.auth',
            'rdrf.context_processors',
            'rdrf.db',
            'rdrf.events',
            'rdrf.forms',
            'rdrf.forms.dynamic',
            'rdrf.forms.fields',
            'rdrf.forms.navigation',
            'rdrf.forms.progress',
            'rdrf.forms.validation',
            'rdrf.forms.widgets',
            'rdrf.helpers',
            'rdrf.models',
            'rdrf.models.definition',
            'rdrf.reports',
            'rdrf.routing',
            'rdrf.security',
            'rdrf.services',
            'rdrf.services.io',
            'rdrf.services.io.content',
            'rdrf.services.io.content.export_import',
            'rdrf.services.io.defs',
            'rdrf.services.io.notifications',
            'rdrf.services.io.reporting',
            'rdrf.services.rest',
            'rdrf.services.rest.urls',
            'rdrf.services.rest.views',
            'rdrf.services.rpc',
            'rdrf.testing',
            'rdrf.testing.behaviour',
            'rdrf.testing.unit',
            'rdrf.views',
            'rdrf.views.decorators',
            'rdrf.workflows',
            'rdrf.workflows.questionnaires',
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
            'schemas',
            'templatetags',
            'management'):
        package_data[package].extend([add_file_for_package(package, subdir, f) for (
            subdir, dirs, files) in os.walk(data_dir) for f in files])

    os.chdir(start_dir)


setup(name='django-rdrf',
      version="4.1.4",
      packages=find_packages(),
      description='RDRF',
      long_description='Rare Disease Registry Framework',
      author='Centre for Comparative Genomics',
      author_email='rdrf@ccg.murdoch.edu.au',
      package_data=package_data,
      zip_safe=False,
      install_requires=requirements
      )
