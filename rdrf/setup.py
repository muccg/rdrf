import os
from setuptools import setup

package_data = {}
start_dir = os.getcwd()

def add_file_for_package(package, subdir, f):
    full_path = os.path.join(subdir, f)
    #print "%s: %s" % (package, full_path)
    return full_path

INSTALL_ONLY_DEPENDENCIES = 'INSTALL_ONLY_DEPENDENCIES' in os.environ

if 'INSTALL_ONLY_DEPENDENCIES' in os.environ:
    packages = []
    package_data = {}
    package_scripts = []
else:
    package_scripts = ["rdrf-manage.py"]

    packages = [ 'rdrf',
                 'registry',
                 'registry.common',
                 'registry.patients',
                 'registry.groups',
                 'registry.genetic',
                 'explorer',
               ]

    for package in ['rdrf', 'registry.common', 'registry.genetic',
                'registry.groups', 'registry.patients']:
        package_data[package] = []
        if "." in package:
            base_dir,package_dir = package.split(".")
            os.chdir(os.path.join(start_dir,base_dir, package_dir))
        else:
            base_dir = package
            os.chdir(os.path.join(start_dir, base_dir))

        for data_dir in ('templates', 'static', 'migrations', 'fixtures', 'features', 'hooks', 'templatetags', 'management'):
            package_data[package].extend(
                [ add_file_for_package(package, subdir, f) for (subdir, dirs, files) in os.walk(data_dir) for f in files])

        os.chdir(start_dir)


setup(name='django-rdrf',
    version="0.8.18",
    packages=packages,
    description='RDRF',
    long_description='Rare Disease Registry Framework',
    author='Centre for Comparative Genomics',
    author_email='web@ccg.murdoch.edu.au',
    package_data= package_data,
    zip_safe=False,
    scripts=package_scripts,
    install_requires=[
        'Django==1.6.10',
        'pymongo',
        'pyyaml',
        'South==0.8.2',
        'django-extensions>=0.7.1',
        'django-picklefield==0.1.9',
        'django-templatetag-sugar==0.1',
        'pyparsing==1.5.6',
        'wsgiref==0.1.2',
        'python-memcached==1.48',
        'django-extensions>=0.7.1',
        'django-messages-ui==0.2.6',
        'ccg-auth==0.3.4',
        'ccg-extras==0.1.7',
        'ccg-django-utils==0.2.1',
        'django-userlog==0.2.1',
        'django-nose',
        'sure==1.2.1',
        'django-templatetag-handlebars==1.2.0',
        'django-iprestrict==0.1',
        'django-suit',
        'django-ajax-selects',
        'pysam==0.8.1',
        'hgvs==0.2.1',
        'django-positions', 
        'django-tastypie==0.11.1',
        'pycountry==1.8',
        'django-countries',
        'hgtools',
        'nose',
        'nose-timer',
        'sphinx',
        'sphinxcontrib-fulltoc',
        'uwsgi==2.0.8',
        'uwsgitop',
        'pyinotify==0.9.4',
        'Werkzeug',
        'psycopg2==2.5.4',
        'six==1.9.0',
        'python-gettext',
        'django-registration-redux',
        'psycopg2==2.5.5'
    ],
    dependency_links=[
        "https://bitbucket.org/ccgmurdoch/ccg-django-utils/downloads/ccg-django-utils-0.2.1.tar.gz",
        "https://bitbucket.org/ccgmurdoch/django-userlog/downloads/django_userlog-0.2.1.tar.gz",
        "https://bitbucket.org/ccgmurdoch/ccg-django-extras/downloads/django-iprestrict-0.1.tar.gz",
        'https://bitbucket.org/ccgmurdoch/ccg-django-extras/downloads/ccg-auth-0.3.4.tar.gz',
        'https://bitbucket.org/ccgmurdoch/ccg-django-extras/downloads/ccg-extras-0.1.7.tar.gz'
    ],
)
