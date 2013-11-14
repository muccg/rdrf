from setuptools import setup

setup(name='rdrf-cdes',
    version='0.1',
    packages=['rdrf_cdes'],
    description='RDRF CDEs',
    long_description='Rare Disease Registry Common Data Elements',
    author='Centre for Comparative Genomics',
    author_email='web@ccg.murdoch.edu.au',
    package_dir= {'rdrf_cdes': 'src/rdrf_cdes'},
    package_data= {'rdrf_cdes': ['templates/rdrf_cdes/cde.html',
                                 'templates/rdrf_cdes/form.html',
                                 'templatetags/get_form.py',
                                 'templatetags/__init__.py']},
    install_requires=[
        'Django==1.5.4',
	    'pymongo',
    ],
)

