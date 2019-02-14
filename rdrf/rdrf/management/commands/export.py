from django.core.management.base import BaseCommand, CommandError

from rdrf.services.io.content import export_import
from rdrf.services.io.content.export_import import definitions
from rdrf.models.definition.models import Registry


class Command(BaseCommand):
    help = 'Export a registry, reference data or CDEs.'

    ExportTypes = [
        getattr(
            definitions.ExportTypes,
            t).code for t in vars(
            definitions.ExportTypes) if t.upper() == t]
    registry_codes = Registry.objects.values_list('code', flat=True)

    def add_arguments(self, parser):
        parser.add_argument('export_type', choices=self.ExportTypes, help='export type')
        parser.add_argument(
            '--registry-code',
            choices=self.registry_codes,
            help='the code of the Registry')
        parser.add_argument('--verbose', action='store_true', help='less verbose output')
        parser.add_argument('--filename', help='the zip file name to export to')

    def handle(self, **options):
        export_type = options['export_type']
        registry_code = options.get('registry_code')

        if export_type in definitions.ExportTypes.registry_types_codes and registry_code is None:
            if len(self.registry_codes) == 1:
                registry_code = self.registry_codes[0]
            else:
                raise CommandError(
                    'When exporting a registry the --registry-code option is mandatory')

        options = {
            'verbose': options.get('verbose'),
            'filename': options.get('filename'),
        }

        if export_type == definitions.ExportTypes.REGISTRY_DEF.code:
            export_import.export_registry_definition(registry_code, **options)
        elif export_type == definitions.ExportTypes.REGISTRY_WITH_DATA.code:
            export_import.export_registry(registry_code, **options)
        elif export_type == definitions.ExportTypes.CDES.code:
            export_import.export_cdes(**options)
        elif export_type == definitions.ExportTypes.REFDATA.code:
            export_import.export_refdata(**options)
