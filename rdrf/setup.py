import os
from setuptools import setup
from rdrf import VERSION

data_files = {}
start_dir = os.getcwd()

def add_file_for_package(package, subdir, f):
    full_path = os.path.join(subdir, f)
    #print "%s: %s" % (package, full_path)
    return full_path

for package in ['rdrf', 'registry.common',
            'registry.groups', 'registry.humangenome', 'registry.patients']:
    data_files[package] = []
    if "." in package:
        base_dir,package_dir = package.split(".")
        os.chdir(os.path.join(start_dir,base_dir, package_dir))
    else:
        base_dir = package
        os.chdir(os.path.join(start_dir, base_dir))

    for data_dir in ('templates', 'static', 'migrations', 'fixtures', 'features', 'templatetags', 'management'):
        data_files[package].extend(
            [ add_file_for_package(package, subdir, f) for (subdir, dirs, files) in os.walk(data_dir) for f in files])

    os.chdir(start_dir)

#print "data_files dict = %s" % data_files

setup(name='django-rdrf',
    version=VERSION,
    packages=[
        'rdrf',
        'registry',
        'registry.common',
        'registry.patients',
        'registry.groups',
        'registry.humangenome'
    ],
    description='RDRF',
    long_description='Rare Disease Registry Framework',
    author='Centre for Comparative Genomics',
    author_email='web@ccg.murdoch.edu.au',
    package_data= data_files,
    zip_safe=False,
    scripts=["rdrf-manage.py"],
    install_requires=[
        'Django==1.6.4',
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
        'ccg-auth==0.3.3',
        'ccg-extras==0.1.7',
        'django-userlog==0.2.1',
        'django-nose',
        'sure==1.2.1',
        'django-templatetag-handlebars==1.2.0',
        'django-iprestrict==0.1',
        'django-suit',
        'django-ajax-selects',
		'hgvs',
		'django-countries'
    ],
    dependency_links = [
        "https://pypi.python.org/packages/source/d/django-templatetag-handlebars/django-templatetag-handlebars-1.2.0.zip",
        "https://bitbucket.org/ccgmurdoch/django-userlog/downloads/django_userlog-0.2.1.tar.gz",
        "https://bitbucket.org/ccgmurdoch/ccg-django-extras/downloads/django-iprestrict-0.1.tar.gz",
        'https://ccg-django-extras.googlecode.com/files/ccg-auth-0.3.3.tar.gz',
        'https://bitbucket.org/ccgmurdoch/ccg-django-extras/downloads/ccg-extras-0.1.7.tar.gz',
    ],
)

