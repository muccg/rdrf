import os
from setuptools import setup

package_data = {}
start_dir = os.getcwd()

requirements=["ccg-django-utils==0.4.2",
              "Django==1.8.14",
              "django-ajax-selects",
              "django-anymail==0.4.2",
              "django-countries",
              "django-extensions>=0.7.1",
              "django-iprestrict==0.4.3",
              "django-messages-ui==0.2.7",
              "django-positions",
              "django-registration-redux==1.3",
              "djangorestframework==3.3.3",
              "django-templatetag-handlebars==1.2.0",
              "django-templatetag-sugar==1.0",
              "django-useraudit==1.2.0",
              "hgtools==6.5.1",
              "openpyxl",
              "polib==1.0.7",
              "psycopg2==2.6.1",
              "pycountry==1.20",
              "pyinotify==0.9.6",
              "pymongo==2.9.3",
              "pyparsing==1.5.7",
              "python-dateutil==2.5.3",
              "python-gettext",
              "python-memcached==1.58",
              "pyyaml",
              "setuptools_scm==1.10.1",
              "six==1.10.0",
              "sphinxcontrib-httpdomain==1.4.0",
              "SQLAlchemy",
              "uwsgi==2.0.13.1",
              "uwsgitop",
              "wsgiref==0.1.2",
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
      version="1.6.0",
      packages=packages,
      description='RDRF',
      long_description='Rare Disease Registry Framework',
      author='Centre for Comparative Genomics',
      author_email='rdrf@ccg.murdoch.edu.au',
      package_data=package_data,
      zip_safe=False,
      install_requires=requirements
      )
