import os
from optparse import make_option
from lettuce import Runner
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Runs lettuce features'

    option_list = BaseCommand.option_list[1:] + (
        make_option('-v', '--verbosity',
                    action='store',
                    dest='verbosity',
                    default='4',
                    type='choice',
                    choices=map(str, range(5)),
                    help='Verbosity level; 0=no output, 1=only dots, 2=only scenario names, 3=colorless output, 4=normal output (colorful)'),

        make_option('--with-xunit',
                    action='store_true',
                    dest='enable_xunit',
                    default=False,
                    help='Output JUnit XML test results to a file'),

        make_option('--xunit-file',
                    action='store',
                    dest='xunit_file',
                    default=None,
                    help='Write JUnit XML to this file. Defaults to lettucetests.xml'),
    )

    def handle(self, *args, **options):
        app_name = 'rdrf'
        module = __import__(app_name)
        path = '%s/features/' % (os.path.dirname(module.__file__))
        runner = Runner(path, verbosity=options.get('verbosity'),
                        enable_xunit=options.get('enable_xunit'),
                        xunit_filename=options.get('xunit_file'),)
        runner.run()
