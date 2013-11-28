import os

from optparse import make_option

from django.core.management.base import BaseCommand, CommandError

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

        make_option('--file',
                    action='store',
                    dest='json_file',
                    default=None,
                    help='JSON file name'),
    )

    def handle(self, *args, **options):
        app_name = 'rdrf'
        module = __import__(app_name)
        path = '%s/fixtures' % (os.path.dirname(module.__file__))
        file_path = '%s/%s' % (path, options.get('json_file'))
        from django.core.management import call_command
        print file_path
        call_command("loaddata", file_path)