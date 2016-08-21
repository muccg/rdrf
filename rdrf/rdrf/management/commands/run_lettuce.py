import os
from optparse import make_option
from lettuce import Runner
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Runs lettuce features'

    option_list = BaseCommand.option_list[1:] + (
        make_option(
            '--lettuce-verbosity',
            action='store',
            dest='lettuce_verbosity',
            default=4,
            type='choice',
            choices=map(str, range(5)),
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
                print('{0} - {1}'.format(i, filename))

        selection = raw_input('Choose a feature file: ')
        while not selection in features:
            selection = raw_input('Choose a feature file: ')

        return features[selection]

    def handle(self, *args, **options):
        app_name = 'rdrf'
        module = __import__(app_name)
        int_or_None = lambda x: None if x is None else int(x)
        features_dir = '{0}/features'.format(os.path.dirname(module.__file__))

        path = None
        if options.get('enable_interactive'):
            path = '{0}/{1}'.format(features_dir, self.interactive_feature(features_dir))
        else:
            path = '{0}/'.format(features_dir)

        runner = Runner(path, verbosity=int_or_None(options.get('lettuce_verbosity')),
                        enable_xunit=options.get('enable_xunit'),
                        xunit_filename=options.get('xunit_file'),)
        runner.run()
