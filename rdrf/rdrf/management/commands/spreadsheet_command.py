import os
from optparse import make_option
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Creates longitudinal report'

    option_list = BaseCommand.option_list[
        1:] +
        (make_option(
            '-r',
            '--registry',
            action='store',
            dest='registry_code',
            help='Registry code'),
         make_option(
            '-s',
            '--start',
            action='store',
            dest='start_date',
            default='1-1-2000',
            help='Start date in DD-MM-YYYY format - defaults to 01-01-2000'),
         make_option(
            '-f',
            '--finish',
            action='store',
            dest='finish_date',
            default='today',
            help="Finish date in DD-MM-YYYY format - defaults to today's date")
         )

    def handle(self, *args, **options):
        app_name = 'rdrf'
        module = __import__(app_name)
        path = '%s/features/' % (os.path.dirname(module.__file__))
        runner = Runner(path, verbosity=options.get('verbosity'),
                        enable_xunit=options.get('enable_xunit'),
                        xunit_filename=options.get('xunit_file'),)
        runner.run()
