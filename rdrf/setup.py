import os
from setuptools import setup, find_packages

package_data = {}
start_dir = os.getcwd()
requirements = [
    "ccg-django-utils==0.4.2",
    "celery==5.0.2",
    "Django==2.2.16",
    "django-anymail==8.1",
    "django-ajax-selects==2.0.0",
    "django-countries==6.1.3",
    "django-extensions==3.0.9",
    "django-iprestrict==1.7.0",
    "django-messages-ui==2.0.2",
    "django-nose==1.4.7",
    "django-positions==0.6.0",
    "django-registration-redux==2.8",
    "djangorestframework==3.12.1",
    "django-storages==1.10.1",
    "django-templatetag-handlebars==1.3.1",
    "django-templatetag-sugar==1.0",
    "django-useraudit==1.7.1",
    "django-uwsgi==0.2.2",
    "geoip2==4.1.0",
    "jsonschema==3.2.0",
    "openpyxl==3.0.5",
    "polib==1.1.0",
    "psycopg2==2.8.6",
    "pycountry==19.8.18",
    "pyinotify==0.9.6",
    "pyodbc==4.0.30",
    "pyparsing==2.4.7",
    "python-dateutil==2.8.1",
    "python-memcached==1.59",
    "pyyaml==5.3.1",
    "setuptools",
    "setuptools_scm==4.1.2",
    "six==1.15.0",
    "SQLAlchemy==1.3.20",
    "uwsgi==2.0.19.1",
    "django-formtools==2.2",
    "django-otp==1.0.1",
    "django-phonenumber-field==2.4.0",
    "django-two-factor-auth==1.12.1",
    "phonenumberslite==8.12.11",
    "Pillow==8.0.1",
    "qrcode==6.1",
    "django-reversion==3.0.8",
    "ua-parser==0.10.0",
    "user-agents==2.2.0",
    "django-user-agents==0.4.0",
    "django-simple-history==2.12.0",
    "django-formtools",
    "python-ldap",
    "django-auth-ldap",
    "django-session-security==2.6.6",
    "Markdown==3.1.1",
    "xhtml2pdf",
    "django-redis==4.12.1",
    "kombu==5.0.2"
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
      version="6.2.2",
      packages=find_packages(),
      description='RDRF',
      long_description='Rare Disease Registry Framework',
      author='Centre for Comparative Genomics',
      author_email='rdrf@ccg.murdoch.edu.au',
      package_data=package_data,
      zip_safe=False,
      install_requires=requirements
      )
