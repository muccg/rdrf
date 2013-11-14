from setuptools import setup

setup(name='django-rdrf',
    version='0.1',
    packages=['rdrf',],
    description='RDRF CDEs',
    long_description='Rare Disease Registry Common Data Elements',
    author='Centre for Comparative Genomics',
    author_email='web@ccg.murdoch.edu.au',
    package_data= {'rdrf': ['templates/rdrf/cde.html',
                                 'templates/rdrf/form.html',
                                 'templatetags/get_form.py',
                                 'templatetags/__init__.py']},
    install_requires=[
        'Django==1.5.4',
	'pymongo',
	'South>=0.7.3',
    ],
    dependency_links = [
        "http://repo.ccgapps.com.au",
    ],
)

