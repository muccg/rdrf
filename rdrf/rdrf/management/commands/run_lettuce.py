import os
from optparse import make_option
from lettuce import Runner
from django.core.management.base import BaseCommand
from django.conf import settings
import logging


# set up the root logger
logger = logging.getLogger()


class Command(BaseCommand):
    help = 'Runs lettuce features'

    option_list = BaseCommand.option_list[1:] + (
        make_option(
            '--lettuce-verbosity',
            action='store',
            dest='lettuce_verbosity',
            default=4,
            type='choice',
            choices=list(map(str, list(range(5)))),
            help='Verbosity level; 0=no output, 1=only dots, 2=only scenario names, 3=colorless output, 4=normal output (colorful)'),
        make_option(
            '--with-xunit',
            action='store_true',
            dest='enable_xunit',
            default=False,
            help='Output JUnit XML test results to a file'),
        make_option(
            '--xunit-file',
            action='store',
            dest='xunit_file',
            default=None,
            help='Write JUnit XML to this file. Defaults to lettucetests.xml'),
        make_option(
            '--interactive',
            action='store_true',
            dest='enable_interactive',
            default=False,
            help='Interactively ask user what feature file to invoke'),
        make_option(
            '--feature',
            action='store',
            dest='single_feature',
            help='Specify a feature file to invoke'),
        make_option(
            '--no-teardown',
            action='store_true',
            dest='disable_teardown',
            default=False,
            help='Don\'t perform tear down after scenario'),
    )

    def interactive_feature(self, features_dir):
        """
        Ask the user what feature file to invoke
        """
        features = {}
        i = 0
        for filename in os.listdir(features_dir):
            if filename.endswith('.feature'):
                i+=1
                features[str(i)] = filename
                print(('{0} - {1}'.format(i, filename)))

        selection = input('Choose a feature file: ')
        while not selection in features:
            selection = input('Choose a feature file: ')

        return features[selection]

    def logging_setup(self):
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
        console.setFormatter(
            logging.Formatter(settings.LOGGING['formatters']['verbose']['format'])
        )
        logger.addHandler(console)

    def get_base_path(self, features_dir, options):
        path = None
        if options.get('enable_interactive'):
            path = '{0}/{1}'.format(features_dir, self.interactive_feature(features_dir))
        elif options.get('single_feature'):
            path = '{0}/{1}'.format(features_dir, options.get('single_feature'))
        else:
            path = '{0}/'.format(features_dir)

        return path

    def env_options(self, options):
        os.environ['LETTUCE_DISABLE_TEARDOWN'] = '1' if options.get('disable_teardown') else '0'

    def handle(self, *args, **options):
        self.logging_setup()
        app_name = 'rdrf'
        module = __import__(app_name)
        int_or_None = lambda x: None if x is None else int(x)
        features_dir = '{0}/features'.format(os.path.dirname(module.__file__))

        base_path = self.get_base_path(features_dir, options)
        self.env_options(options)

        runner = Runner(base_path, verbosity=int_or_None(options.get('lettuce_verbosity')),
                        enable_xunit=options.get('enable_xunit'),
                        xunit_filename=options.get('xunit_file'),)

        runner.run()
