from django.core.management.base import BaseCommand

from rdrf.services.io.content.export_import import import_zipfile, inspect_zipfile, definitions


class Command(BaseCommand):
    help = 'Imports data (registry, reference data, CDEs) from an exported zip file.'

    import_types = [
        getattr(
            definitions.ExportTypes,
            t).code for t in vars(
            definitions.ExportTypes) if t.upper() == t]

    def add_arguments(self, parser):
        parser.add_argument('zipfile')
        parser.add_argument('--verbose', action='store_true', help='less verbose output')
        parser.add_argument(
            '--inspect',
            action='store_true',
            help='display information about the zip file')
        parser.add_argument(
            '--simulate',
            action='store_true',
            help='perform a simulation of the import')
        parser.add_argument(
            '--force',
            action='store_true',
            help='force through import ignoring warnings')
        parser.add_argument('--import-type', choices=self.import_types, help='import type')

    def handle(self, **options):
        from django.conf import settings
        settings.IMPORT_MODE = True
        zipfile = options['zipfile']
        verbose = options.get('verbose')
        inspect = options.get('inspect')
        simulate = options.get('simulate')
        force = options.get('force')
        import_type = options.get('import_type')

        if inspect:
            inspect_zipfile(zipfile)
            return

        import_zipfile(
            zipfile,
            import_type=import_type,
            verbose=verbose,
            simulate=simulate,
            force=force)
        settings.IMPORT_MODE = False
