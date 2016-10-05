import os
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Runs load fixture command'

    def add_arguments(self, parser):
        parser.add_argument('--file',
                            action='store',
                            dest='json_file',
                            default=None,
                            help='JSON file name')

    def handle(self, *args, **options):
        app_name = 'rdrf'
        module = __import__(app_name)
        path = '%s/fixtures' % (os.path.dirname(module.__file__))
        file_path = '%s/%s' % (path, options.get('json_file'))
        from django.core.management import call_command
        print(file_path)
        call_command("loaddata", file_path)
