from django.core.management import BaseCommand
from rdrf.models.definition.models import Registry


class Command(BaseCommand):
    help = "Set the registry version"

    def add_arguments(self, parser):
        parser.add_argument('--code',
                            action='store',
                            dest='code',
                            default=None,
                            help='The registry code')
        parser.add_argument('--ver',
                            action='store',
                            dest='version',
                            default=None,
                            help='The new registry version to be set')

    def handle(self, *args, **options):
        code = options.get("code")
        version = options.get("version")
        Registry.objects.filter(code=code).update(version=version)
