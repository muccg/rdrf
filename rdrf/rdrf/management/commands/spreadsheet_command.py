from optparse import make_option
from django.core.management.base import BaseCommand
from rdrf.services.io.reporting.spreadsheet_report import SpreadSheetReport
from rdrf.models.definition.models import Registry


def get_triple(registry_model, form_name, section_code, cde_code):
    for form_model in registry_model.forms:
        if form_model.name == form_name:
            for section_model in form_model.section_models:
                if section_model.code == section_code:
                    for cde_model in section_model.cde_models:
                        if cde_model.code == cde_code:
                            return form_model, section_model, cde_model


class Command(BaseCommand):
    help = 'Creates longitudinal report'

    option_list = BaseCommand.option_list[1:] + (make_option(
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
        help="Finish date in DD-MM-YYYY format - defaults to today's date"),
    )

    def handle(self, *args, **options):
        try:
            registry_model = Registry.objects.get(
                code=options.get("registry_code", None))
        except Registry.DoesNotExist:
            raise

        triples = [get_triple(registry_model, "Clinical", "sectionxxx", "CDEHeight")]

        report = SpreadSheetReport(None,
                                   registry_model,
                                   [],
                                   triples,
                                   None)

        report.generate()
